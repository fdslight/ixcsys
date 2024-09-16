#!/usr/bin/env python3

import sys, os, signal, json, time
import dns.message

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
import ixc_syscore.secDNS.handlers.msg_forward as msg_forward

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
        cls.release()

    if os.path.isfile(PID_FILE): os.remove(PID_FILE)
    sys.exit(0)


class service(dispatcher.dispatcher):
    __debug = None
    __scgi_fd = None

    # 连接列表,每一个dict代表一个连接,分别为文件描述符,失败次数,更新时间
    # 格式为[{"fd":0,"fail_count":0,"time":0}]
    __dot_fds = None

    __msg_fwd_fd = None

    __dot_configs = None
    __secDNS_configs = None

    def init_func(self, debug):
        global_vars["ixcsys.secDNS"] = self

        self.__debug = debug
        self.__dot_fds = []
        self.__dot_configs = []
        self.__msg_fwd_fd = -1

        RPCClient.wait_processes(["router", "DNS", ])

        print("AA")

        self.create_poll()
        print("BB")
        self.start_scgi()

        self.__msg_fwd_fd = self.create_handler(-1, msg_forward)

        self.start()

    @property
    def dot_conf_path(self):
        fpath = "%s/dot.json" % os.getenv("IXC_MYAPP_CONF_DIR")
        return fpath

    @property
    def secDNS_conf_path(self):
        fpath = "%s/secDNS.json" % os.getenv("IXC_MYAPP_CONF_DIR")
        return fpath

    @property
    def dot_configs(self):
        return self.__dot_configs

    @property
    def configs(self):
        return self.__secDNS_configs

    def tell_conn_ok(self, _id: int, fd: int):
        """告知连接OK"""
        o = self.__dot_fds[_id]
        o["fd"] = fd
        o["time"] = time.time()

    def tell_conn_fail(self, _id: int):
        """告知连接失败
        """
        o = self.__dot_fds[_id]
        o["fd"] = -1
        o["time"] = time.time()

    def start(self):
        self.load_configs()

        pub = self.__secDNS_configs.get("public", {})
        try:
            enable = bool(int(pub.get("enable", 0)))
        except ValueError:
            enable = False

        if not enable: return

        i = 0
        for o in self.__dot_configs:
            t = {"fd": "-1", "time": time.time()}
            self.__dot_fds.append(t)
            i += 1

    def stop(self):
        for o in self.__dot_fds:
            fd = o["fd"]
            if fd >= 0:
                self.delete_handler(fd)
                continue
            ''''''
        self.__dot_fds = []
        ''''''

    def reset(self):
        self.stop()
        self.start()

    def myloop(self):
        pass

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

        self.__dot_configs = js

        secDNS_conf = configfile.ini_parse_from_file(self.secDNS_conf_path)
        self.__secDNS_configs = secDNS_conf

    def save_configs(self):
        s = json.dumps(self.__dot_configs)
        f = open(self.dot_conf_path, "w")
        f.write(s)
        f.close()

    @property
    def debug(self):
        return self.__debug

    @property
    def ca_path(self):
        path = "%s/data/ca-bundle.crt" % os.getenv("IXC_SHARED_DATA_DIR")
        return path

    def get_server_ip(self, host, enable_ipv6=False):
        """获取服务器IP
        :param host:
        :return:
        """
        if netutils.is_ipv4_address(host): return host
        if netutils.is_ipv6_address(host): return host

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

    def handle_msg_from_local(self, message: bytes):
        # 首先查找缓存是否存在,如果存在缓存,那么直接返回

        # 逐个发送数据包到DNS服务器
        i = 0
        for o in self.__dot_fds:
            fd = o["fd"]
            if fd < 0:
                conf = self.__dot_configs[i]
                fd = self.create_handler(-1, dot_handler.dot_client, i, conf["host"], hostname=conf["hostname"])
            if fd < 0: continue
            self.get_handler(fd).send_to_server(message)
            o += 1

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
