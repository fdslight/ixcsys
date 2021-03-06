#!/usr/bin/env python3
import os, sys, signal, json

sys.path.append(os.getenv("IXC_SYS_DIR"))

if not os.path.isdir(os.getenv("IXC_MYAPP_TMP_DIR")): os.mkdir(os.getenv("IXC_MYAPP_TMP_DIR"))

import pywind.evtframework.evt_dispatcher as dispatcher
import pywind.lib.proc as proc
import pywind.lib.configfile as cfg
import pywind.web.handlers.scgi as scgi

import ixc_syslib.pylib.logging as logging
import ixc_syslib.web.route as webroute
import ixc_syslib.pylib.RPCClient as RPCClient

import ixc_syscore.sysadm.handlers.httpd as httpd

PID_FILE = "%s/proc.pid" % os.getenv("IXC_MYAPP_TMP_DIR")


def __stop_service():
    pid = proc.get_pid(PID_FILE)
    if pid < 0: return

    os.kill(pid, signal.SIGINT)


def __start_service(debug):
    if not debug and os.path.isfile(PID_FILE):
        print("the sysadm process exists")
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
    __httpd_fd = None
    __httpd_fd6 = None

    __httpd_ssl_fd = None
    __httpd_ssl_fd6 = None

    __debug = None

    __httpd_cfg_path = None
    __httpd_configs = None

    __scgi_fd = None

    def load_configs(self):
        self.__httpd_configs = cfg.ini_parse_from_file(self.__httpd_cfg_path)

    def write_to_configs(self):
        pass

    def http_start(self):
        manage_addr = self.get_manage_addr()

        listen = self.__httpd_configs["listen"]
        ssl_cfg = self.__httpd_configs["ssl"]

        enable_ipv6 = bool(int(listen["enable_ipv6"]))
        enable_ssl = bool(int(listen["enable_ssl"]))

        port = int(listen["port"])

        ssl_key = ssl_cfg["key"]
        ssl_cert = ssl_cfg["cert"]

        self.__httpd_fd = self.create_handler(-1, httpd.httpd_listener, (manage_addr, port,), is_ipv6=False)
        if enable_ipv6:
            self.__httpd_fd6 = self.create_handler(-1, httpd.httpd_listener, ("::", port,), is_ipv6=True)
        if not enable_ssl: return

        self.__httpd_ssl_fd = self.create_handler(-1, httpd.httpd_listener, (manage_addr, port,), is_ipv6=False,
                                                  ssl_on=True, ssl_key=ssl_key, ssl_cert=ssl_cert)
        self.__httpd_ssl_fd6 = self.create_handler(-1, httpd.httpd_listener, ("::", port,), is_ipv6=False,
                                                   ssl_on=True, ssl_key=ssl_key, ssl_cert=ssl_cert)

    def init_func(self, debug):
        self.__httpd_fd = -1
        self.__httpd_fd6 = -1
        self.__httpd_ssl_fd = -1
        self.__httpd_ssl_fd6 = -1

        self.__debug = debug

        self.__httpd_cfg_path = "%s/httpd.ini" % os.getenv("IXC_MYAPP_CONF_DIR")

        self.__scgi_fd = -1

        self.load_configs()
        self.create_poll()

        self.wait_router_proc()
        self.start_scgi()
        self.http_start()

    def start_scgi(self):
        scgi_configs = {
            "use_unix_socket": True,
            "listen": os.getenv("IXC_MYAPP_SCGI_PATH"),
            "application": webroute.app_route(),
            "debug": self.__debug
        }

        self.__scgi_fd = self.create_handler(-1, scgi.scgid_listener, scgi_configs)
        self.get_handler(self.__scgi_fd).after()

    def get_manage_addr(self):
        ipaddr = RPCClient.fn_call("router", "/config", "manage_addr_get")

        return ipaddr

    def myloop(self):
        pass

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

    @property
    def debug(self):
        return self.__debug

    def release(self):
        if self.__scgi_fd:
            self.delete_handler(self.__scgi_fd)
            self.__scgi_fd = -1
        if self.__httpd_fd > 0:
            self.delete_handler(self.__httpd_fd)
            self.__httpd_fd = -1
        if self.__httpd_fd6 > 0:
            self.delete_handler(self.__httpd_fd6)
            self.__httpd_fd6 = -1
        if self.__httpd_ssl_fd > 0:
            self.delete_handler(self.__httpd_ssl_fd)
            self.__httpd_ssl_fd = -1
        if self.__httpd_ssl_fd6 > 0:
            self.delete_handler(self.__httpd_ssl_fd6)
            self.__httpd_ssl_fd6 = -1

        if os.path.exists(os.getenv("IXC_MYAPP_SCGI_PATH")): os.remove(os.getenv("IXC_MYAPP_SCGI_PATH"))


def main():
    __helper = "ixc_syscore/sysadm helper: start | stop | debug"

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
