#!/usr/bin/env python3

import sys, os, signal, json, time
import dns.message

sys.path.append(os.getenv("IXC_SYS_DIR"))

if not os.path.isdir(os.getenv("IXC_MYAPP_TMP_DIR")): os.mkdir(os.getenv("IXC_MYAPP_TMP_DIR"))

import pywind.evtframework.evt_dispatcher as dispatcher
import pywind.lib.proc as proc
import pywind.web.handlers.scgi as scgi
import pywind.lib.netutils as netutils

from pywind.global_vars import global_vars

import ixc_syslib.web.route as webroute
import ixc_syslib.pylib.logging as logging
import ixc_syslib.pylib.RPCClient as RPCClient

import ixc_syscore.secDNS.handlers.dot as dot_handler

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
    __dot_fds = None

    __dot_configs = None

    def init_func(self, debug):
        global_vars["ixcsys.secDNS"] = self

        self.__debug = debug
        self.__dot_fds = []
        self.__dot_configs = []

        RPCClient.wait_processes(["router", "DNS", ])

        self.create_poll()
        self.start_scgi()
        self.start()

    @property
    def dot_conf_path(self):
        fpath = "%s/dot.json" % os.getenv("IXC_MYAPP_CONF_DIR")
        return fpath

    def start(self):
        pass

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
        pass

    def release(self):
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
