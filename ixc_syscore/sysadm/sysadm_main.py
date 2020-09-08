#!/usr/bin/env python3
import os, sys, signal

sys.path.append(os.getenv("IXC_SYS_DIR"))

if not os.path.isdir(os.getenv("IXC_MYAPP_TMP_DIR")): os.mkdir(os.getenv("IXC_MYAPP_TMP_DIR"))

import pywind.evtframework.evt_dispatcher as dispatcher
import pywind.lib.proc as proc
import pywind.lib.configfile as cfg

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

    def load_configs(self):
        self.__httpd_configs = cfg.ini_parse_from_file(self.__httpd_cfg_path)

    def write_to_configs(self):
        pass

    def service_start(self):
        listen = self.__httpd_configs["listen"]

    def init_func(self, debug):
        self.__httpd_fd = -1
        self.__httpd_fd6 = -1
        self.__httpd_ssl_fd = -1
        self.__httpd_ssl_fd6 = -1

        self.__debug = debug

        self.__httpd_cfg_path = "%s/httpd.ini" % os.getenv("IXC_MYAPP_CONF_DIR")

        self.load_configs()
        self.create_poll()

        self.service_start()

    @property
    def debug(self):
        return self.__debug

    def release(self):
        pass


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
