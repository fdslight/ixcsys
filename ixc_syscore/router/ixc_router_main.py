#!/usr/bin/env python3

import sys, os, signal, time

sys.path.append(os.getenv("IXC_SYS_DIR"))

if not os.path.isdir(os.getenv("IXC_MYAPP_TMP_DIR")): os.mkdir(os.getenv("IXC_MYAPP_TMP_DIR"))

from pywind.global_vars import global_vars

import pywind.evtframework.evt_dispatcher as dispatcher
import pywind.lib.proc as proc
import pywind.web.handlers.scgi as scgi
import ixc_syslib.web.route as webroute
import ixc_syslib.pylib.logging as logging
import ixc_syslib.pylib.RPCClient as RPC

import ixc_syscore.router.handlers.conn_mon as conn_mon_handler

PID_FILE = "%s/proc.pid" % os.getenv("IXC_MYAPP_TMP_DIR")


def __stop_service():
    pid = proc.get_pid(PID_FILE)
    if pid < 0: return

    os.kill(pid, signal.SIGINT)


def __start_service(debug):
    if not debug and os.path.isfile(PID_FILE):
        print("the ixc_router process exists")
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

    __is_linux = None
    __scgi_fd = None

    __network_status = None
    __net_status_up_time = None

    __chk_host_info = None

    def report_network_status(self, is_ok: bool):
        self.__network_status = is_ok

    def clear_os_route(self, is_ipv6=False):
        """清除系统的路由表
        """
        if is_ipv6:
            fdst = os.popen("ip -6 route")
        else:
            fdst = os.popen("ip route")

        __list = []
        for line in fdst:
            line = line.replace("\n", "")
            line = line.replace("\r", "")
            p = line.find("dev")
            if p < 1: continue
            __list.append(line[0:p].strip())

        for x in __list:
            if is_ipv6:
                cmd = "ip -6 route del %s" % x
            else:
                cmd = "ip route del %s" % x
            os.system(cmd)

    @property
    def is_linux(self):
        return self.__is_linux

    @property
    def debug(self):
        return self.__debug

    def check_network_status(self):
        """检查网络状态
        """
        # 未设置那么不检查
        if not self.__chk_host_info: return
        now = time.time()
        # 10分钟检查一次
        if now - self.__net_status_up_time < 600: return

        host, addr, is_ipv6 = self.__chk_host_info
        fd = conn_mon_handler.conn_mon_client(host, addr, is_ipv6=is_ipv6)

    def release(self):
        if self.__scgi_fd:
            self.delete_handler(self.__scgi_fd)

        if os.path.exists(os.getenv("IXC_MYAPP_SCGI_PATH")): os.remove(os.getenv("IXC_MYAPP_SCGI_PATH"))

        os.system("%s/ixc_router_core stop" % os.getenv("IXC_MYAPP_DIR"))
        self.__scgi_fd = -1

    def start_scgi(self):
        scgi_configs = {
            "use_unix_socket": True,
            "listen": os.getenv("IXC_MYAPP_SCGI_PATH"),
            "application": webroute.app_route()
        }
        self.__scgi_fd = self.create_handler(-1, scgi.scgid_listener, scgi_configs)
        self.get_handler(self.__scgi_fd).after()

    def init_func(self, debug):
        self.__debug = debug
        self.__scgi_fd = -1
        self.__network_status = True
        self.__net_status_up_time = time.time()

        RPC.wait_proc("init")

        self.clear_os_route()
        self.clear_os_route(is_ipv6=True)

        if os.path.exists(os.getenv("IXC_MYAPP_SCGI_PATH")): os.remove(os.getenv("IXC_MYAPP_SCGI_PATH"))

        os.system("%s/ixc_router_core start" % os.getenv("IXC_MYAPP_DIR"))

        if not self.debug:
            sys.stdout = logging.stdout()
            sys.stderr = logging.stderr()

        self.create_poll()

        global_vars["ixcsys.runtime"] = self

        self.start_scgi()

    @property
    def rpc_sock_path(self):
        return "/tmp/ixcsys/router/rpc.sock"

    def myloop(self):
        self.check_network_status()


def main():
    __helper = "ixc_syscore/router helper: start | stop | debug"
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
