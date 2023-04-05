#!/usr/bin/env python3

import sys, os, signal, time, struct, json, pickle
import dns.message

sys.path.append(os.getenv("IXC_SYS_DIR"))

if not os.path.isdir(os.getenv("IXC_MYAPP_TMP_DIR")): os.mkdir(os.getenv("IXC_MYAPP_TMP_DIR"))

import pywind.evtframework.evt_dispatcher as dispatcher
import pywind.lib.proc as proc
import pywind.lib.configfile as conf
import pywind.web.handlers.scgi as scgi
import pywind.lib.netutils as netutils

from pywind.global_vars import global_vars

import ixc_syslib.pylib.logging as logging
import ixc_syslib.pylib.RPCClient as RPCClient
import ixc_syslib.web.route as webroute

import ixc_syscore.DNS.handlers.dns_proxyd as dns_proxyd
import ixc_syscore.DNS.pylib.rule as rule
import ixc_syscore.DNS.pylib.os_resolv as os_resolv
import ixc_syscore.DNS.pylib.sec_rule as sec_rule

PID_FILE = "%s/proc.pid" % os.getenv("IXC_MYAPP_TMP_DIR")


def __stop_service():
    pid = proc.get_pid(PID_FILE)
    if pid < 0: return

    os.kill(pid, signal.SIGINT)


def __start_service(debug):
    if not debug and os.path.isfile(PID_FILE):
        print("the ixc_dns_main process exists")
        return

    if not debug:
        pid = os.fork()
        if pid != 0: sys.exit(0)

        os.setsid()
        os.umask(0)
        pid = os.fork()

        if pid != 0: sys.exit(0)

        proc.write_pid(PID_FILE, os.getpid())

    cls = service(debug)

    try:
        cls.ioloop(debug)
    except KeyboardInterrupt:
        cls.release()
    except:
        cls.release()
        logging.print_error(debug=debug)

    if os.path.isfile(PID_FILE): os.remove(PID_FILE)
    sys.exit(0)


class service(dispatcher.dispatcher):
    __dns_server = None
    __dns_client = None

    __dns_server6 = None
    __dns_client6 = None

    __dns_configs = None
    __dns_conf_path = None

    __sec_rules = None
    __sec_rule_path = None

    # WAN到LAN的DNS ID映射
    __id_wan2lan = None
    __matcher = None

    __up_time = None

    __scgi_fd = None
    __cur_dns_id = None

    # 是否重定向DNS结果
    __forward_result = None

    __wan_ok = None
    __up_time = None

    def init_func(self, *args, **kwargs):
        global_vars["ixcsys.DNS"] = self

        self.__dns_server = -1
        self.__dns_client = -1

        self.__dns_server6 = -1
        self.__dns_client6 = -1

        self.__dns_conf_path = "%s/dns.ini" % os.getenv("IXC_MYAPP_CONF_DIR")
        self.__sec_rule_path = "%s/sec_rules.txt" % os.getenv("IXC_MYAPP_CONF_DIR")

        self.__id_wan2lan = {}

        self.__matcher = rule.matcher()
        self.__up_time = time.time()
        self.__scgi_fd = -1
        self.__cur_dns_id = 1
        self.__forward_result = False
        self.__wan_ok = False

        RPCClient.wait_processes(["router", ])

        self.create_poll()
        self.start_dns()
        self.start_scgi()
        self.add_ns_os_resolv()

    def get_os_ip6_managet_addr(self):
        """获取操作系统的IPv6管理地址
        """
        cmd="ip addr | grep inet6 | grep "


    def rule_forward_set(self, port: int):
        self.get_handler(self.__dns_client).set_forward_port(port)

    def load_configs(self):
        self.__dns_configs = conf.ini_parse_from_file(self.__dns_conf_path)

    def load_sec_rules(self):
        self.__sec_rules = sec_rule.parse_from_file(self.__sec_rule_path)
        for rule in self.__sec_rules:
            self.matcher.add_rule(rule, "drop", None)

    def start_dns(self):
        self.load_configs()
        self.load_sec_rules()

        manage_addr = self.get_manage_addr()
        ipv4 = self.__dns_configs["ipv4"]
        ipv6 = self.__dns_configs["ipv6"]

        self.__dns_client = self.create_handler(-1, dns_proxyd.proxy_client, ipv4["main_dns"], ipv4["second_dns"],
                                                is_ipv6=False)
        self.__dns_client6 = self.create_handler(-1, dns_proxyd.proxy_client, ipv6["main_dns"], ipv6["second_dns"],
                                                 is_ipv6=True)
        self.__dns_server = self.create_handler(-1, dns_proxyd.proxyd, (manage_addr, 53), is_ipv6=False)

        # 此处检查IPv6方式,如果是静态下发那么丢弃DNS AAAA请求
        lan_configs = RPCClient.fn_call("router", "/config", "lan_config_get")
        if_cfg = lan_configs["if_config"]

    def start_scgi(self):
        scgi_configs = {
            "use_unix_socket": True,
            "listen": os.getenv("IXC_MYAPP_SCGI_PATH"),
            "application": webroute.app_route()
        }
        self.__scgi_fd = self.create_handler(-1, scgi.scgid_listener, scgi_configs)
        self.get_handler(self.__scgi_fd).after()

    def get_manage_addr(self):
        """获取管理地址
        """
        ipaddr = RPCClient.fn_call("router", "/config", "manage_addr_get")

        return ipaddr

    def get_dns_id(self):
        dns_id = self.__cur_dns_id
        self.__cur_dns_id += 1
        # 此处重置DNS ID
        if self.__cur_dns_id > 0xfffe: self.__cur_dns_id = 1

        return dns_id

    # def set_route(self, subnet: str, prefix: int, is_ipv6=False):
    #    RPCClient.fn_call("router", "/config", "add_route", subnet, prefix, None, is_ipv6=is_ipv6)

    def send_to_dnsserver(self, message: bytes, is_ipv6=False):
        """发送到DNS服务器
        """
        if is_ipv6 and self.__dns_client6 < 0: return
        if not is_ipv6 and self.__dns_client < 0: return

        if is_ipv6:
            fd = self.__dns_client6
        else:
            fd = self.__dns_client

        self.get_handler(fd).send_request_msg(message)

    def handle_msg_from_dnsserver(self, message: bytes, is_ipv6=False):
        """处理来自于DNS服务器的消息
        """
        dns_id, = struct.unpack("!H", message[0:2])
        # 找不到映射记录那么直接删除
        if dns_id not in self.__id_wan2lan: return
        if is_ipv6:
            fd = self.__dns_server6
        else:
            fd = self.__dns_server

        o = self.__id_wan2lan[dns_id]
        x_dns_id = o["id"]
        new_msg = b"".join([struct.pack("!H", x_dns_id), message[2:]])
        self.get_handler(fd).send_msg(new_msg, o["address"])

        if not o["from_forward"] and self.__forward_result:
            try:
                msg_obj = dns.message.from_wire(new_msg)
            except:
                del self.__id_wan2lan[dns_id]
                return
            for rrset in msg_obj.answer:
                for cname in rrset:
                    flags = False
                    ip = cname.__str__()
                    is_ipv6 = False
                    if netutils.is_ipv4_address(ip):
                        flags = True
                    elif netutils.is_ipv6_address(ip):
                        flags = True
                        is_ipv6 = True
                    else:
                        continue
                    if not flags: continue
                    msg = {
                        "action": "dns_result",
                        "priv_data": None,
                        "message": (ip, is_ipv6,)
                    }
                    self.get_handler(self.__dns_client).send_forward_msg(pickle.dumps(msg))
                ''''''
            ''''''
        # 此处删除记录
        del self.__id_wan2lan[dns_id]

    def handle_msg_from_dnsclient(self, message: bytes, address: tuple, is_ipv6=False):
        """处理来自于DNS客户端的消息
        """
        if not self.__wan_ok: return
        if len(message) < 15: return

        dns_id, = struct.unpack("!H", message[0:2])
        new_dns_id = self.get_dns_id()

        if new_dns_id < 0:
            logging.print_error("cannot get DNS ID for DNS proxy")
            return
        try:
            msg_obj = dns.message.from_wire(message)
        except:
            return

        _list = [struct.pack("!H", new_dns_id), message[2:]]
        new_msg = b"".join(_list)

        self.__id_wan2lan[new_dns_id] = {"id": dns_id, "address": address, "is_ipv6": is_ipv6,
                                         "time": time.time(), "from_forward": False}

        questions = msg_obj.question
        if len(questions) != 1:
            self.send_to_dnsserver(new_msg, is_ipv6=is_ipv6)
            return

        q = questions[0]
        host = b".".join(q.name[0:-1]).decode("iso-8859-1")
        match_rs = self.__matcher.match(host)

        logging.print_info("DNS_QUERY: %s from %s" % (host, address[0]))

        if not match_rs:
            self.send_to_dnsserver(new_msg, is_ipv6=is_ipv6)
            return

        action = match_rs["action"]
        # 如果规则为丢弃那么直接丢弃该DNS请求
        if action == "drop":
            del self.__id_wan2lan[new_dns_id]
            return
        # 发送DNS数据到其他应用程序,如果找不到文件号那么丢弃数据包
        if self.__dns_client < 0: return

        msg = {
            "action": action,
            "priv_data": match_rs["priv_data"],
            "message": new_msg
        }

        self.__id_wan2lan[new_dns_id]["from_forward"] = True
        self.get_handler(self.__dns_client).send_forward_msg(pickle.dumps(msg))

    @property
    def matcher(self):
        return self.__matcher

    @property
    def configs(self):
        return self.__dns_configs

    @property
    def sec_rules(self):
        return self.__sec_rules

    def is_auto(self):
        return bool(int(self.__dns_configs["public"]["enable_auto"]))

    def get_nameservers(self, is_ipv6=False):
        if is_ipv6:
            return self.get_handler(self.__dns_client6).get_nameservers()
        else:
            return self.get_handler(self.__dns_client).get_nameservers()

    def set_nameservers(self, ns1: str, ns2: str, is_ipv6=False):
        if is_ipv6:
            self.get_handler(self.__dns_client6).set_nameservers(ns1, ns2)
        else:
            self.get_handler(self.__dns_client).set_nameservers(ns1, ns2)

    def forward_dns_result(self):
        self.__forward_result = True

    def get_forward(self):
        return self.get_handler(self.__dns_client).get_port()

    def add_sec_rule(self, rule: str):
        if rule in self.__sec_rules:
            return
        self.__sec_rules.append(rule)
        self.matcher.add_rule(rule, "drop", None)

    def del_sec_rule(self, rule: str):
        if rule not in self.__sec_rules: return
        self.__sec_rules.remove(rule)
        self.matcher.del_rule(rule)

    def save_configs(self):
        conf.save_to_ini(self.__dns_configs, self.__dns_conf_path)
        self.save_sec_rules()

    def save_sec_rules(self):
        sec_rule.save_to_file(self.__sec_rules, self.__sec_rule_path)

    def release(self):
        if self.__scgi_fd > 0: self.delete_handler(self.__scgi_fd)
        if self.__dns_server > 0: self.delete_handler(self.__dns_server)
        if self.__dns_client > 0: self.delete_handler(self.__dns_client)
        if self.__dns_server6 > 0: self.delete_handler(self.__dns_server6)
        if self.__dns_client6 > 0: self.delete_handler(self.__dns_client6)

        if os.path.exists(os.getenv("IXC_MYAPP_SCGI_PATH")): os.remove(os.getenv("IXC_MYAPP_SCGI_PATH"))

    def auto_clean(self):
        now_t = time.time()

        # 设置每隔一段时间清理一次DNS映射记录
        if now_t - self.__up_time < 5: return

        dels = []
        for _id in self.__id_wan2lan:
            t = self.__id_wan2lan[_id]["time"]
            if now_t - t < 5: continue
            dels.append(_id)

        for _id in dels:
            del self.__id_wan2lan[_id]

    def add_ns_os_resolv(self):
        """加入nameserver到操作系统resolv中
        :return:
        """
        manage_addr = self.get_manage_addr()
        cls = os_resolv.resolv()
        # 如果存在那么不加入
        if cls.exists(manage_addr): return

        _list = cls.get_os_resolv()
        _list.insert(0, ("nameserver", manage_addr))
        cls.write_to_file(_list)

    def myloop(self):
        self.auto_clean()

        if not self.__wan_ok:
            now = time.time()
            if now - self.__up_time < 10: return
            self.__wan_ok = RPCClient.fn_call("router", "/config", "wan_ready_ok")
        ''''''


def main():
    __helper = "ixc_syscore/DNS helper: start | stop | debug"
    if len(sys.argv) != 2:
        print(__helper)
        return

    action = sys.argv[1]
    if action not in ("start", "stop", "debug",):
        print(__helper)
        return

    if action == "stop":
        __stop_service()
        return

    if action == "debug":
        debug = True
    else:
        debug = False

    __start_service(debug)


if __name__ == '__main__': main()
