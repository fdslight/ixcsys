#!/usr/bin/env python3

import sys, os, signal, json, time

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
    __log_count = None
    __log_max = None
    __errlog_fdst = None

    __errlog_path = None
    __syslog_path = None

    def init_func(self, debug):
        global_vars["ixcsys.init"] = self

        self.__debug = debug
        self.__logs = []
        self.__log_count = 0
        self.__log_max = 100
        self.__errlog_fd = None

        self.__errlog_path = "/var/log/ixcsys_error.log"
        self.__syslog_path = "/var/log/ixcsys_syslog.log"

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

        if level not in level_map: return

        if self.debug:
            fmt_msg = "\r\n\r\napplication:%s\r\nlevel:%s\r\n%s" % (name, level_map[level], message,)
            if level == logging.LEVEL_ERR:
                sys.stdout.write(fmt_msg)
            else:
                sys.stderr.write(fmt_msg)
            return

        if not self.debug:
            self.__errlog_fdst = open(self.__errlog_path, "a")

        if not self.debug and level == logging.LEVEL_ERR:
            self.write_err_log(name, message)
            return

        o = {"level": level_map[level], "application": name, "message": message}
        if self.__log_count > self.__log_max: self.__logs.pop(0)
        self.__logs.append(o)

    def write_err_log(self, name: str, message: str):
        s1 = time.strftime("%Y-%m-%d %H:%M:%S %Z")
        w = "%s\r\napplication:%s\r\nmessage:\r\n%s\r\n" % (s1, name, message)

        self.__errlog_fdst.write(w)
        self.__errlog_fdst.flush()

    def save_log_to_file(self):
        fpath = self.__syslog_path
        s = json.dumps(self.__logs)
        with open(fpath, "wb") as f: f.write(s.encode())
        f.close()

    def get_syslog(self, from_file=False):
        if not from_file: return self.__logs

        fpath = self.__syslog_path
        with open(fpath, "rb") as f: byte_s = f.read()
        f.close()
        return json.loads(byte_s.decode())

    def get_errlog(self):
        with open(self.__errlog_path, "r") as f:
            s = f.read()
        f.close()

        return s

    def release(self):
        if os.path.exists(os.getenv("IXC_MYAPP_SCGI_PATH")): os.remove(os.getenv("IXC_MYAPP_SCGI_PATH"))

        if self.__log_fd > 0: self.delete_handler(self.__log_fd)
        if self.__errlog_fdst: self.__errlog_fdst.close()

        self.save_log_to_file()


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
