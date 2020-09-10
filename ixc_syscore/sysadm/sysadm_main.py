#!/usr/bin/env python3
import os, sys, signal, json

sys.path.append(os.getenv("IXC_SYS_DIR"))

if not os.path.isdir(os.getenv("IXC_MYAPP_TMP_DIR")): os.mkdir(os.getenv("IXC_MYAPP_TMP_DIR"))

import pywind.evtframework.evt_dispatcher as dispatcher
import pywind.lib.proc as proc
import pywind.lib.configfile as cfg

import pywind.web.handlers.scgi as scgi

import ixc_syslib.pylib.logging as logging
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

    __httpd_listen_addr = None
    __httpd_listen_addr6 = None

    __scgi_fd = None

    def load_configs(self):
        self.__httpd_configs = cfg.ini_parse_from_file(self.__httpd_cfg_path)

    def write_to_configs(self):
        pass

    def service_start(self):
        self.__httpd_fd = self.create_handler(-1, httpd.httpd_listener, (self.__httpd_listen_addr, 8080,))

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

        self.__scgi_fd=self.create_handler(-1,scgi.scgid_listener,)

        signal.signal(signal.SIGUSR1, self.__sig_load_service)

    def myloop(self):
        pass

    @property
    def debug(self):
        return self.__debug

    def release(self):
        if self.__scgi_fd > 0:
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

    def __sig_load_service(self, signum, frame):
        info_file = "%s/ipconf.json" % os.getenv("IXC_MYAPP_TMP_DIR")

        with open(info_file, "r") as f: s = f.read()
        f.close()

        o = json.loads(s)

        self.__httpd_listen_addr = o["ip"]
        self.__httpd_listen_addr6 = o["ipv6"]

        self.service_start()


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
