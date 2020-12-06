#!/usr/bin/env python3

import sys, os, signal, time, struct, random
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
        logging.print_error()

    if os.path.isfile(PID_FILE): os.remove(PID_FILE)
    sys.exit(0)


class service(dispatcher.dispatcher):
    __dns_server = None
    __dns_client = None

    __dns_server6 = None
    __dns_client6 = None

    __dns_configs = None
    __dns_conf_path = None

    # WAN到LAN的DNS ID映射
    __id_wan2lan = None
    # LAN到WAN的DNS ID映射
    __id_lan2wan = None

    __matcher = None

    __empty_dns_ids = None
    __up_time = None

    __scgi_fd = None

    def init_func(self, *args, **kwargs):
        global_vars["ixcsys.DNS"] = self

        self.__dns_server = -1
        self.__dns_client = -1

        self.__dns_server6 = -1
        self.__dns_client6 = -1

        self.__dns_conf_path = "%s/dns.ini" % os.getenv("IXC_MYAPP_CONF_DIR")

        self.__id_wan2lan = {}
        self.__id_lan2wan = {}

        self.__matcher = rule.matcher()
        self.__empty_dns_ids = []
        self.__up_time = time.time()
        self.__scgi_fd = -1

        self.create_poll()
        self.wait_router_proc()
        self.start_dns()
        self.start_scgi()

    def load_configs(self):
        self.__dns_configs = conf.ini_parse_from_file(self.__dns_conf_path)

    def wait_router_proc(self):
        """等待路由进程
        """
        while 1:
            ok = RPCClient.RPCReadyOk("router")
            if not ok:
                time.sleep(5)
            else:
                break
            ''''''
        return

    def start_dns(self):
        self.load_configs()
        manage_addr = self.get_manage_addr()
        ipv4 = self.__dns_configs["ipv4"]

        self.__dns_client = self.create_handler(-1, dns_proxyd.proxy_client, ipv4["main_dns"], ipv4["second_dns"],
                                                is_ipv6=False)
        self.__dns_server = self.create_handler(-1, dns_proxyd.proxyd, (manage_addr, 53), is_ipv6=False)

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
        rs = -1
        if self.__empty_dns_ids: return self.__empty_dns_ids.pop(0)
        for i in range(256):
            dns_id = random.randint(1, 0xfffe)
            if dns_id in self.__id_wan2lan: continue
            rs = dns_id
        return rs

    def put_dns_id(self, _id: int):
        self.__empty_dns_ids.append(_id)

    def set_route(self, subnet: str, prefix: int, is_ipv6=False):
        RPCClient.fn_call("router", "/runtime", "add_route", subnet, prefix, None, is_ipv6=is_ipv6)

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
        action = o["action"]

        new_msg = b"".join([struct.pack("!H", x_dns_id), message[2:]])

        # 未设置动作那么直接发送
        if not action:
            self.get_handler(fd).send_msg(new_msg, o["address"])
            return

        act_name = action["action"]
        # 重定向以及自动设置路由
        if act_name != "forward_and_auto_route":
            self.get_handler(fd).send_msg(new_msg, o["address"])
            return

        try:
            msg_obj = dns.message.from_wire(new_msg)
        except:
            return

        for rrset in msg_obj.answer:
            for cname in rrset:
                ip = cname.__str__()
                if netutils.is_ipv4_address(ip):
                    self.set_route(ip, 32, is_ipv6=False)
                    continue
                if netutils.is_ipv6_address(ip):
                    self.set_route(ip, 128, is_ipv6=True)
                    continue
                ''''''
            ''''''
        self.get_handler(fd).send_msg(new_msg, o["address"])

    def handle_msg_from_dnsclient(self, message: bytes, address: tuple, is_ipv6=False):
        """处理来自于DNS客户端的消息
        """
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

        self.__id_lan2wan[dns_id] = {"id": new_dns_id, "up_time": time.time()}
        self.__id_wan2lan[new_dns_id] = {"id": dns_id, "address": address, "is_ipv6": is_ipv6, "action": None}

        questions = msg_obj.question
        if len(questions) != 1 or msg_obj.opcode != 0:
            self.send_to_dnsserver(new_msg, is_ipv6=is_ipv6)
            return
        q = questions[0]
        host = b".".join(q.name[0:-1]).decode("iso-8859-1")
        match_rs = self.__matcher.match(host)

        if not match_rs:
            self.send_to_dnsserver(new_msg, is_ipv6=is_ipv6)
            return

        action = match_rs["action"]
        # 如果规则为丢弃那么直接丢弃该DNS请求
        # 这里rewrite暂时作为丢弃处理
        if action == "drop" or action == "rewrite":
            del self.__id_lan2wan[dns_id]
            del self.__id_wan2lan[new_dns_id]
            return
        self.__id_wan2lan[new_dns_id]["action"] = match_rs
        # 发送DNS数据到其他应用程序,如果找不到文件号那么丢弃数据包
        if self.__dns_client < 0: return
        self.get_handler(self.__dns_client).send_forward_msg(message)

    @property
    def matcher(self):
        return self.__matcher

    @property
    def configs(self):
        return self.__dns_configs

    def save_configs(self):
        conf.save_to_ini(self.__dns_configs, self.__dns_conf_path)

    def release(self):
        if os.path.exists(os.getenv("IXC_MYAPP_SCGI_PATH")): os.remove(os.getenv("IXC_MYAPP_SCGI_PATH"))
        if self.__dns_server > 0: self.delete_handler(self.__dns_server)
        if self.__dns_client > 0: self.delete_handler(self.__dns_client)
        if self.__dns_server6 > 0: self.delete_handler(self.__dns_server6)
        if self.__dns_client6 > 0: self.delete_handler(self.__dns_client6)

    def auto_clean(self):
        now_t = time.time()

        # 设置每隔一段时间清理一次DNS映射记录
        if now_t - self.__up_time < 5: return

        dels = []
        for _id in self.__id_lan2wan:
            o = self.__id_lan2wan[_id]
            up_time = o["up_time"]
            # 查询时间大于3s那么清除映射记录
            if now_t - up_time < 3: continue
            dels.append(_id)
        for _id in dels:
            o = self.__id_lan2wan[_id]
            _id2 = o["id"]
            self.put_dns_id(_id)
            del self.__id_lan2wan[_id]
            del self.__id_wan2lan[_id2]

        self.__up_time = time.time()

    def myloop(self):
        self.auto_clean()


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
