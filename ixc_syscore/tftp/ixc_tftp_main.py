#!/usr/bin/env python3

import sys, os, signal, time

sys.path.append(os.getenv("IXC_SYS_DIR"))

if not os.path.isdir(os.getenv("IXC_MYAPP_TMP_DIR")): os.mkdir(os.getenv("IXC_MYAPP_TMP_DIR"))

import pywind.evtframework.evt_dispatcher as dispatcher
import pywind.lib.proc as proc
import pywind.lib.configfile as conf

import ixc_syslib.pylib.logging as logging
import ixc_syslib.pylib.RPCClient as RPCClient

import ixc_syscore.tftp.handlers.tftpd as tftpd

PID_FILE = "%s/proc.pid" % os.getenv("IXC_MYAPP_TMP_DIR")


def __stop_service():
    pid = proc.get_pid(PID_FILE)
    if pid < 0: return

    os.kill(pid, signal.SIGINT)


def __start_service(debug):
    if not debug and os.path.isfile(PID_FILE):
        print("the ixc_tftp_main process exists")
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
    __conf_path = None
    __tftpd_fd = None
    __tftpd_fd6 = None

    __debug = None
    __configs = None

    __sessions = None

    def init_func(self, debug):
        self.__debug = debug
        self.__conf_path = "%s/tftpd.ini" % os.getenv("IXC_MYAPP_CONF_DIR")
        self.__tftpd_fd = -1
        self.__tftpd_fd6 = -1
        self.__sessions = {}

        self.create_poll()
        self.wait_router_proc()
        self.load_configs()
        self.start_tftp()

    def myloop(self):
        if self.__tftpd_fd > 0: self.get_handler(self.__tftpd_fd).loop()
        if self.__tftpd_fd6 > 0: self.get_handler(self.__tftpd_fd6).loop()
        if self.__sessions:
            self.set_default_io_wait_time(2)
        else:
            self.set_default_io_wait_time(10)

    @property
    def sessions(self):
        return self.__sessions

    @property
    def configs(self):
        return self.__configs

    def load_configs(self):
        self.__configs = conf.ini_parse_from_file(self.__conf_path)

    def save_configs(self):
        pass

    def get_manage_addr(self):
        ipaddr = RPCClient.fn_call("router", "/runtime", "get_manage_ipaddr")

        return ipaddr

    def start_tftp(self):
        conf = self.__configs["conf"]
        enable_ipv6 = bool(int(conf["enable_ipv6"]))

        self.__tftpd_fd = self.create_handler(-1, tftpd.tftpd, self.get_manage_addr(), is_ipv6=False)
        if enable_ipv6: self.__tftpd_fd6 = self.create_handler(-1, tftpd.tftpd, "::", is_ipv6=True)

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

    def release(self):
        if self.__tftpd_fd > 0: self.delete_handler(self.__tftpd_fd)
        if self.__tftpd_fd6 > 0: self.delete_handler(self.__tftpd_fd6)


def main():
    __helper = "ixc_syscore/tftp helper: start | stop | debug"
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
