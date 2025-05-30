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

    __logs_generic = None
    __logs_important = None

    __logs_generic_count = None
    __logs_important_count = None

    __log_max = None

    __errlog_path = None
    __syslog_path = None
    __scgi_fd = None

    # 故障日志最大文件大小(bytes)
    __errlog_file_max_size = None
    __up_time = None

    def init_func(self, debug):
        global_vars["ixcsys.init"] = self

        self.__debug = debug
        self.__logs_generic = []
        self.__logs_important = []
        self.__logs_generic_count = 0
        self.__logs_important_count = 0
        self.__log_max = 512

        self.__errlog_path = "/var/log/ixcsys_error.log"
        self.__syslog_path = "/var/log/ixcsys_syslog.log"

        # 限制最大为256KB
        self.__errlog_file_max_size = 256 * 1024
        self.__up_time = time.time()

        self.load_syslog()

        self.create_poll()
        self.start_scgi()
        self.log_start()

    def log_start(self):
        self.__log_fd = self.create_handler(-1, syslog.syslogd)

    def myloop(self):
        self.auto_clean_err_log()
        self.auto_sync_log_to_file()

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

        if level == logging.LEVEL_ERR:
            self.write_err_log(name, message)
            return

        o = {"level": level_map[level], "application": name, "message": message,
             "time": time.strftime("%Y-%m-%d %H:%M:%S %Z")}

        while 1:
            if level == logging.LEVEL_INFO:
                _list = self.__logs_generic
                count = self.__logs_generic_count
            else:
                _list = self.__logs_important
                count = self.__logs_important_count
            if count >= self.__log_max:
                _list.pop(0)
                if level == logging.LEVEL_INFO:
                    self.__logs_generic_count -= 1
                else:
                    self.__logs_important_count -= 1
                ''''''
            else:
                break
            ''''''
        if level == logging.LEVEL_INFO:
            self.__logs_generic_count += 1
        else:
            self.__logs_important_count += 1

        _list.append(o)

    def write_err_log(self, name: str, message: str):
        s1 = time.strftime("%Y-%m-%d %H:%M:%S %Z")
        w = "%s\r\napplication:%s\r\nmessage:\r\n%s\r\n" % (s1, name, message)

        fdst = open(self.__errlog_path, "a")

        fdst.write(w)
        fdst.close()

    def save_log_to_file(self):
        fpath = self.__syslog_path

        new_list = self.__logs_generic + self.__logs_important

        s = json.dumps(new_list)
        with open(fpath, "wb") as f: f.write(s.encode())
        f.close()

    def get_info_syslog(self):
        return self.__logs_generic

    def get_alert_syslog(self):
        return self.__logs_important

    def load_syslog(self):
        fpath = self.__syslog_path

        if not os.path.isfile(fpath): return

        with open(fpath, "rb") as f:
            byte_s = f.read()
        f.close()
        try:
            r = json.loads(byte_s.decode())
        except:
            return
        ''''''

        for dic in r:
            try:
                if dic["level"].lower() == "info":
                    self.__logs_generic.append(dic)
                else:
                    self.__logs_important.append(dic)
                ''''''
            except KeyError:
                continue
            ''''''
        self.__logs_generic_count = len(self.__logs_generic)
        self.__logs_important_count = len(self.__logs_important)

    def get_errlog(self):
        if not os.path.isfile(self.__errlog_path): return ""
        with open(self.__errlog_path, "r") as f:
            s = f.read()
        f.close()

        return s

    def auto_clean_err_log(self):
        """自动清理故障日志
        """
        if not os.path.isfile(self.__errlog_path): return
        fstat = os.stat(self.__errlog_path)
        if fstat.st_size > self.__errlog_file_max_size:
            fdst = open(self.__errlog_path, "w")
            fdst.close()
        return

    def auto_sync_log_to_file(self):
        # 自动同步普通日志
        now = time.time()
        if now - self.__up_time >= 86400:
            self.save_log_to_file()
            self.__up_time = now
        return

    def release(self):
        if self.__log_fd > 0: self.delete_handler(self.__log_fd)
        if self.__scgi_fd > 0: self.delete_handler(self.__scgi_fd)

        if os.path.exists(os.getenv("IXC_MYAPP_SCGI_PATH")): os.remove(os.getenv("IXC_MYAPP_SCGI_PATH"))

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
