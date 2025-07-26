#!/usr/bin/env python3
import sys, os, signal, json, time

import dns.message, dns.resolver

sys.path.append(os.getenv("IXC_SYS_DIR"))

if not os.path.isdir(os.getenv("IXC_MYAPP_TMP_DIR")): os.mkdir(os.getenv("IXC_MYAPP_TMP_DIR"))

import pywind.evtframework.evt_dispatcher as dispatcher
import pywind.lib.proc as proc
import pywind.web.handlers.scgi as scgi
import pywind.lib.netutils as netutils
import pywind.lib.configfile as configfile

from pywind.global_vars import global_vars

import ixc_syslib.web.route as webroute
import ixc_syslib.pylib.logging as logging
import ixc_syslib.pylib.RPCClient as RPCClient

import ixc_syscore.secDNS.handlers.dot as dot_handler
import ixc_syscore.secDNS.handlers.msg_forward as msg_fwd

PID_FILE = "%s/proc.pid" % os.getenv("IXC_MYAPP_TMP_DIR")


def __stop_service():
    pid = proc.get_pid(PID_FILE)
    if pid < 0: return

    os.kill(pid, signal.SIGINT)


def __start_service(debug):
    if not debug and os.path.isfile(PID_FILE):
        print("the ixc_secDNS_main process exists")
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
        logging.print_error()
        cls.release()

    if os.path.isfile(PID_FILE): os.remove(PID_FILE)
    sys.exit(0)


class service(dispatcher.dispatcher):
    __debug = None
    __scgi_fd = None

    __msg_fwd_fd = None

    __dot_configs = None
    __secDNS_configs = None
    __enable_sec_dns = None

    __up_time = None

    __dns_fds = None

    def init_func(self, debug):
        global_vars["ixcsys.secDNS"] = self

        self.__debug = debug
        self.__dot_configs = []
        self.__msg_fwd_fd = -1
        self.__enable_sec_dns = False
        self.__up_time = time.time()
        self.__dns_fds = {}

        RPCClient.wait_processes(["router", "DNS", ])

        self.create_poll()
        self.start_scgi()
        self.start_msg_forward()

        self.start()

    def tell_conn_fail(self, host):
        """取消空闲连接
        """
        if host in self.__dns_fds: del self.__dns_fds[host]

    def start_msg_forward(self):
        self.__msg_fwd_fd = self.create_handler(-1, msg_fwd.msg_fwd)

    def stop_msg_forward(self):
        if self.__msg_fwd_fd >= 0: self.delete_handler(self.__msg_fwd_fd)

    @property
    def dot_conf_path(self):
        fpath = "%s/dot.json" % os.getenv("IXC_MYAPP_CONF_DIR")
        return fpath

    @property
    def secDNS_conf_path(self):
        fpath = "%s/secDNS.ini" % os.getenv("IXC_MYAPP_CONF_DIR")
        return fpath

    @property
    def dot_configs(self):
        return self.__dot_configs

    @property
    def configs(self):
        return self.__secDNS_configs

    def get_domains(self):
        dot_configs = self.__dot_configs
        results = []
        for conf in dot_configs:
            host = conf['host']
            if not netutils.is_ipv4_address(host) and not netutils.is_ipv6_address(host):
                results.append(host)
            ''''''
        return results

    def set_dns_forward(self):
        # 获取key以及本地端口
        key = self.get_handler(self.__msg_fwd_fd).key
        port = self.get_handler(self.__msg_fwd_fd).port

        RPCClient.fn_call("DNS", "/config", "set_sec_dns_forward", port, key)

        # 设置本地UDP DNS服务器,使其转发流量到本进程
        RPCClient.fn_call("DNS", "/config", "enable_sec_dns", True)
        domains = self.get_domains()
        RPCClient.fn_call("DNS", "/config", "add_sec_dns_domains", domains)

    def start(self):
        self.load_configs()

        pub = self.__secDNS_configs.get("public", {})
        try:
            enable = bool(int(pub.get("enable", 0)))
        except ValueError:
            enable = False

        self.__enable_sec_dns = enable

        if not enable: return

        logging.print_info("start secDNS")
        if len(self.__dot_configs) == 0: return

        self.set_dns_forward()

    def stop(self):
        fds = []
        for host, fd in self.__dns_fds.items():
            fds.append(fd)
        for fd in fds:
            self.delete_handler(fd)
        self.__dns_fds = {}
        # 停止本地UDP DNS服务器流量转发
        RPCClient.fn_call("DNS", "/config", "enable_sec_dns", False)
        domains = self.get_domains()
        RPCClient.fn_call("DNS", "/config", "del_sec_dns_domains", domains)
        logging.print_info("stop secDNS")
        ''''''

    def reset(self):
        self.stop()
        self.start()

    def myloop(self):
        now = time.time()
        # 每隔一段时间监控一次,避免DNS查询过慢
        if now - self.__up_time >= 10:
            self.monitor_dot_server_conn()
            self.__up_time = now
        return

    def load_configs(self):
        with open(self.dot_conf_path, "r") as f:
            s = f.read()
        f.close()
        try:
            js = json.loads(s)
        except:
            logging.print_error("wrong dot config file")
            return

        if not isinstance(js, list):
            logging.print_error("wrong dot config file,it should be a list")
            return

        for conf in js:
            use_ipv6 = False
            if "force_ipv6" not in conf:
                if netutils.is_ipv6_address(conf["host"]):
                    use_ipv6 = True
                ''''''
            else:
                use_ipv6 = conf['force_ipv6']
            conf['force_ipv6'] = use_ipv6

        self.__dot_configs = js

        secDNS_conf = configfile.ini_parse_from_file(self.secDNS_conf_path)
        self.__secDNS_configs = secDNS_conf

    def save_dot_configs(self):
        s = json.dumps(self.__dot_configs)
        f = open(self.dot_conf_path, "w")
        f.write(s)
        f.close()

    def save_secDNS_configs(self):
        configfile.save_to_ini(self.__secDNS_configs, self.secDNS_conf_path)

    def dot_host_add(self, host: str, hostname: str, comment: str, port=853, force_ipv6=False):
        exists = False
        # 首先检查是否存在
        for o in self.__dot_configs:
            if o["host"] != host: continue
            exists = True
            break
        # 如果存在那么不添加
        if exists: return
        self.stop()
        self.__dot_configs.append(
            {"host": host, "port": port, "comment": comment, "hostname": hostname, "force_ipv6": force_ipv6})
        self.save_dot_configs()
        self.start()

    def dot_host_del(self, host: str):
        # 首先停止所有连接
        self.stop()
        del_idx = -1
        i = 0
        for o in self.__dot_configs:
            if o["host"] != host:
                i += 1
                continue
            del_idx = i
            break
        if del_idx < 0: return
        del self.__dot_configs[del_idx]
        self.save_dot_configs()
        self.start()

    def secDNS_enable(self, enable: bool):
        if "public" not in self.__secDNS_configs:
            self.__secDNS_configs["public"] = {}
        self.__secDNS_configs["public"]["enable"] = int(enable)
        self.save_secDNS_configs()

        self.reset()

    @property
    def debug(self):
        return self.__debug

    @property
    def ca_path(self):
        path = "%s/ca-bundle.crt" % os.getenv("IXC_SHARED_DATA_DIR")
        return path

    def get_server_ip(self, host, enable_ipv6=False):
        """获取服务器IP
        :param host:
        :return:
        """
        if netutils.is_ipv4_address(host) and enable_ipv6: return None
        if netutils.is_ipv6_address(host) and not enable_ipv6: return None

        resolver = dns.resolver.Resolver()

        resolver.timeout = 5
        resolver.lifetime = 5

        try:
            try:
                if enable_ipv6:
                    rs = resolver.resolve(host, "AAAA")
                else:
                    rs = resolver.resolve(host, "A")
                ''''''
            except AttributeError:
                try:
                    if enable_ipv6:
                        rs = resolver.query(host, "AAAA")
                    else:
                        rs = resolver.query(host, "A")
                    ''''''
                except:
                    return None
                ''''''
        except:
            return None

        ipaddr = None

        for anwser in rs:
            ipaddr = anwser.__str__()
            break

        return ipaddr

    def start_scgi(self):
        scgi_configs = {
            "use_unix_socket": True,
            "listen": os.getenv("IXC_MYAPP_SCGI_PATH"),
            "application": webroute.app_route()
        }
        self.__scgi_fd = self.create_handler(-1, scgi.scgid_listener, scgi_configs)
        self.get_handler(self.__scgi_fd).after()

    def send_to_dns_server(self, message: bytes):
        # 检查一遍DoT服务器是否都在线
        self.monitor_dot_server_conn()
        # 逐个发送数据包到DNS服务器
        for o in self.__dot_configs:
            host = o["host"]
            if host not in self.__dns_fds: continue

            fd = self.__dns_fds[host]
            self.get_handler(fd).send_to_server(message)
        return

    def monitor_dot_server_conn(self):
        """监控DoT服务器连接,如连接不存在,那么创建连接
        """
        for o in self.__dot_configs:
            host = o["host"]
            force_ipv6 = o.get("force_ipv6", False)
            # 考虑是IP地址的情况,强制修正
            if netutils.is_ipv4_address(host):
                force_ipv6 = False
            if netutils.is_ipv6_address(host):
                force_ipv6 = True
            if host not in self.__dns_fds:
                try:
                    port = int(o.get("port", '853'))
                except ValueError:
                    port = 853
                fd = self.create_handler(-1, dot_handler.dot_client, o["host"], port=port, hostname=o["hostname"],
                                         is_ipv6=force_ipv6)
                if fd < 0: continue
                self.__dns_fds[host] = fd
            ''''''
        return

    def handle_msg_from_local(self, message: bytes):
        # 首先查找缓存是否存在,如果存在缓存,那么直接返回
        self.send_to_dns_server(message)

    def handle_msg_from_server(self, message: bytes):
        # 发送消息到本地
        self.get_handler(self.__msg_fwd_fd).send_msg_to_local(message)

    def release(self):
        self.stop()
        if self.__msg_fwd_fd > 0:
            self.delete_handler(self.__msg_fwd_fd)
        if self.__scgi_fd > 0: self.delete_handler(self.__scgi_fd)
        if os.path.exists(os.getenv("IXC_MYAPP_SCGI_PATH")): os.remove(os.getenv("IXC_MYAPP_SCGI_PATH"))


def main():
    __helper = "ixc_syscore/secDNS helper: start | stop | debug"
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
