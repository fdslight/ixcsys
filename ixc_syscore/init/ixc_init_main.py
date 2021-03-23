#!/usr/bin/env python3

import sys, os, signal

sys.path.append(os.getenv("IXC_SYS_DIR"))

if not os.path.isdir(os.getenv("IXC_MYAPP_TMP_DIR")): os.mkdir(os.getenv("IXC_MYAPP_TMP_DIR"))

import pywind.evtframework.evt_dispatcher as dispatcher
import pywind.lib.proc as proc
import pywind.web.handlers.scgi as scgi

from pywind.global_vars import global_vars

import ixc_syslib.pylib.logging as logging
import ixc_syslib.web.route as webroute
import ixc_syscore.init.handlers.syslog as syslog

PID_FILE = "%s/proc.pid" % os.getenv("IXC_MYAPP_TMP_DIR")


def __stop_service():
    pid = proc.get_pid(PID_FILE)
    if pid < 0: return

    os.kill(pid, signal.SIGINT)


def __start_service(debug):
    if not debug and os.path.isfile(PID_FILE):
        print("the ixc_init_main process exists")
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
    __debug = None
    __log_fd = None
    __logs = None

    def init_func(self, debug):
        global_vars["ixcsys.init"] = self

        self.__debug = debug
        self.__logs = {
            logging.LEVEL_INFO: {},
            logging.LEVEL_ALERT: {},
            logging.LEVEL_ERR: {}
        }
        self.create_poll()
        self.start_scgi()
        self.log_start()

    def log_start(self):
        self.__log_fd = self.create_handler(-1, syslog.syslogd)

    def myloop(self):
        pass

    @property
    def debug(self):
        return self.__debug

    def start_scgi(self):
        scgi_configs = {
            "use_unix_socket": True,
            "listen": os.getenv("IXC_MYAPP_SCGI_PATH"),
            "application": webroute.app_route()
        }
        self.__scgi_fd = self.create_handler(-1, scgi.scgid_listener, scgi_configs)
        self.get_handler(self.__scgi_fd).after()

    def log_write(self, level: int, name: str, message: str):
        t = message.replace("\n", "")
        t = t.replace("\r", "")
        if not t: return

        level_map = {
            logging.LEVEL_INFO: "INFO",
            logging.LEVEL_ALERT: "ALERT",
            logging.LEVEL_ERR: "ERROR"
        }
        if self.debug:
            fmt_msg = "\r\n\r\napplication:%s\r\nlevel:%s\r\n%s" % (name, level_map[level], message,)
            if level == logging.LEVEL_ERR:
                sys.stdout.write(fmt_msg)
            else:
                sys.stderr.write(fmt_msg)
            return
        o = self.__logs[level]
        #if name not in o:
        #    o[name] = []
        #z = o[name]
        #z.append(message)

    def release(self):
        if os.path.exists(os.getenv("IXC_MYAPP_SCGI_PATH")): os.remove(os.getenv("IXC_MYAPP_SCGI_PATH"))
        if self.__log_fd > 0: self.delete_handler(self.__log_fd)


def main():
    __helper = "ixc_syscore/init helper: start | stop | debug"
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