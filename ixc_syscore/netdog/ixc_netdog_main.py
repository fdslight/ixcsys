#!/usr/bin/env python3

import sys, os, signal, json, time, struct

sys.path.append(os.getenv("IXC_SYS_DIR"))

if not os.path.isdir(os.getenv("IXC_MYAPP_TMP_DIR")): os.mkdir(os.getenv("IXC_MYAPP_TMP_DIR"))

import pywind.evtframework.evt_dispatcher as dispatcher
import pywind.lib.proc as proc
import pywind.web.handlers.scgi as scgi
import pywind.lib.configfile as cfg

from pywind.global_vars import global_vars

import ixc_syslib.pylib.logging as logging
import ixc_syslib.pylib.RPCClient as RPCClient
import ixc_syslib.web.route as webroute

PID_FILE = "%s/proc.pid" % os.getenv("IXC_MYAPP_TMP_DIR")


def __stop_service():
    pid = proc.get_pid(PID_FILE)
    if pid < 0: return

    os.kill(pid, signal.SIGINT)


def __start_service(debug):
    if not debug and os.path.isfile(PID_FILE):
        print("the ixc_netdog_main process exists")
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
    __msg_fd = None
    __scgi_fd = None

    __consts = None
    __configs = None

    __conf_path = None
    # 包分析器工作数目
    __worker_num = None

    def init_func(self, debug):
        global_vars["ixcsys.netdog"] = self

        self.__conf_path = "%s/netdog.ini" % os.getenv("IXC_MYAPP_CONF_DIR")

        self.__debug = debug
        self.__msg_fd = -1
        self.__configs = {}
        self.__scgi_fd = -1
        self.__worker_num = 2

        RPCClient.wait_processes(["router"])

        self.__consts = RPCClient.fn_call("router", "/config", "get_all_consts")
        RPCClient.fn_call("router", "/config", "traffic_copy_peer_num_set", 1)

        for i in range(self.__worker_num):
            cmd = "%s/ixc_netdog_anylized start %s" % (os.getenv("IXC_MYAPP_RELATIVE_DIR"), i)
            os.system(cmd)
            time.sleep(3)
        # 首先关闭流量拷贝
        self.create_poll()
        self.start_scgi()

        self.traffic_anylize_enable(True)

    def myloop(self):
        pass

    @property
    def debug(self):
        return self.__debug

    @property
    def configs(self):
        return self.__configs

    def traffic_anylize_enable(self, enable: bool):
        RPCClient.fn_call("router", "/config", "traffic_cpy_enable", enable)

    def load_configs(self):
        conf = cfg.ini_parse_from_file(self.__conf_path)

    def save_configs(self):
        pass

    def start_scgi(self):
        scgi_configs = {
            "use_unix_socket": True,
            "listen": os.getenv("IXC_MYAPP_SCGI_PATH"),
            "application": webroute.app_route()
        }
        self.__scgi_fd = self.create_handler(-1, scgi.scgid_listener, scgi_configs)
        self.get_handler(self.__scgi_fd).after()

    def release(self):
        self.traffic_anylize_enable(False)

        for i in range(self.__worker_num):
            cmd = "%s/ixc_netdog_anylized stop %s" % (os.getenv("IXC_MYAPP_RELATIVE_DIR"), i)
            os.system(cmd)

        if self.__scgi_fd > 0: self.delete_handler(self.__scgi_fd)
        if os.path.exists(os.getenv("IXC_MYAPP_SCGI_PATH")): os.remove(os.getenv("IXC_MYAPP_SCGI_PATH"))


def main():
    __helper = "ixc_syscore/netdog helper: start | stop | debug"
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
