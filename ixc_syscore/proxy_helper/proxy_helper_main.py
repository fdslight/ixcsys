#!/usr/bin/env python3

import sys, os, signal, time

sys.path.append(os.getenv("IXC_SYS_DIR"))

if not os.path.isdir(os.getenv("IXC_MYAPP_TMP_DIR")): os.mkdir(os.getenv("IXC_MYAPP_TMP_DIR"))

import pywind.evtframework.evt_dispatcher as dispatcher
import pywind.lib.proc as proc
import pywind.web.handlers.scgi as scgi

from pywind.global_vars import global_vars

import ixc_syslib.pylib.logging as logging
import ixc_syslib.pylib.RPCClient as RPCClient
import ixc_syslib.web.route as webroute

import ixc_syscore.proxy_helper.handlers.netpkt as netpkt

import ixc_syscore.proxy_helper.pylib.proxy_helper as proxy_helper

PID_FILE = "%s/proc.pid" % os.getenv("IXC_MYAPP_TMP_DIR")


def __stop_service():
    pid = proc.get_pid(PID_FILE)
    if pid < 0: return

    os.kill(pid, signal.SIGINT)


def __start_service(debug):
    if not debug and os.path.isfile(PID_FILE):
        print("the proxy_helper process exists")
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
    __proxy_helper = None

    __tcp_sessions = None
    __rand_key = None

    __fd = None
    __consts = None

    def init_func(self, debug):
        global_vars["ixcsys.proxy_helper"] = self

        self.__debug = debug
        self.__tcp_sessions = {}
        self.__rand_key = os.urandom(16)
        self.__fd = -1

        self.create_poll()
        self.wait_router_proc()
        self.start_scgi()
        self.start()

    def netpkt_sent_cb(self, byte_data: bytes):
        pass

    def tcp_conn_ev_cb(self, session_id: bytes, src_addr: str, dst_addr: str, sport: int, dport: int, is_ipv6: bool):
        pass

    def tcp_recv_cb(self, session_id: bytes, window_size: int, is_ipv6: bool, data: bytes):
        pass

    def tcp_close_ev_cb(self, session_id: bytes, is_ipv6: bool):
        pass

    def udp_recv_cb(self, saddr: str, daddr: str, sport: int, dport: int, is_udplite: bool, is_ipv6: bool, data: bytes):
        print(saddr, daddr, sport, dport, data)

    def start(self):
        self.__proxy_helper = proxy_helper.proxy_helper(
            self.netpkt_sent_cb,
            self.tcp_conn_ev_cb,
            self.tcp_recv_cb,
            self.tcp_recv_cb,
            self.udp_recv_cb
        )
        consts = RPCClient.fn_call("router", "/runtime", "get_all_consts")
        self.__fd = self.create_handler(-1, netpkt.nspkt_handler)
        port = self.get_handler(self.__fd).get_sock_port()
        self.get_handler(self.__fd).set_message_auth(self.__rand_key)

        RPCClient.fn_call("router", "/netpkt", "unset_fwd_port", consts["IXC_FLAG_ROUTE_FWD"])
        RPCClient.fn_call("router", "/netpkt", "unset_fwd_port", consts["IXC_FLAG_SRC_FILTER"])

        ok, message = RPCClient.fn_call("router", "/netpkt", "set_fwd_port", consts["IXC_FLAG_SRC_FILTER"],
                                        self.__rand_key, port)
        ok, message = RPCClient.fn_call("router", "/netpkt", "set_fwd_port", consts["IXC_FLAG_ROUTE_FWD"],
                                        self.__rand_key, port)
        self.__consts = consts
        # 进行路由测试
        ok, message = RPCClient.fn_call("router", "/runtime", "add_route", "8.8.8.8", 32, "0.0.0.0", is_ipv6=False)

    @property
    def proxy_helper(self):
        return self.__proxy_helper

    @property
    def consts(self):
        return self.__consts

    def stop(self):
        if self.handler_exists(self.__fd):
            self.delete_handler(self.__fd)
            self.__fd = -1

    def myloop(self):
        self.__proxy_helper.myloop()

    def get_manage_addr(self):
        ipaddr = RPCClient.fn_call("router", "/config", "manage_addr_get")

        return ipaddr

    def http_proxy_url(self):
        return "/"

    def start_scgi(self):
        scgi_configs = {
            "use_unix_socket": True,
            "listen": os.getenv("IXC_MYAPP_SCGI_PATH"),
            "application": webroute.app_route()
        }
        self.__scgi_fd = self.create_handler(-1, scgi.scgid_listener, scgi_configs)
        self.get_handler(self.__scgi_fd).after()

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
        if os.path.exists(os.getenv("IXC_MYAPP_SCGI_PATH")): os.remove(os.getenv("IXC_MYAPP_SCGI_PATH"))
        self.stop()


def main():
    __helper = "ixc_syscore/proxy_helper: start | stop | debug"
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
