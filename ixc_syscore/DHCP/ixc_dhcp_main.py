#!/usr/bin/env python3
import sys, os, signal, time

sys.path.append(os.getenv("IXC_SYS_DIR"))

if not os.path.isdir(os.getenv("IXC_MYAPP_TMP_DIR")): os.mkdir(os.getenv("IXC_MYAPP_TMP_DIR"))

import pywind.evtframework.evt_dispatcher as dispatcher
import pywind.lib.proc as proc
import pywind.lib.configfile as conf
import pywind.web.handlers.scgi as scgi

from pywind.global_vars import global_vars

import ixc_syscore.DHCP.handlers.dhcpd as dhcp
import ixc_syscore.DHCP.pylib.dhcp_client as dhcp_client
import ixc_syscore.DHCP.pylib.dhcp_server as dhcp_server

import ixc_syslib.web.route as webroute
import ixc_syslib.pylib.logging as logging
import ixc_syslib.pylib.RPCClient as RPCClient

PID_FILE = "%s/proc.pid" % os.getenv("IXC_MYAPP_TMP_DIR")


def __stop_service():
    pid = proc.get_pid(PID_FILE)
    if pid < 0: return

    os.kill(pid, signal.SIGINT)


def __start_service(debug):
    if not debug and os.path.isfile(PID_FILE):
        print("the ixc_dhcp_main process exists")
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
    __scgi_fd = None
    __dhcp_fd = None

    __dhcp_client = None
    __dhcp_server = None

    __hostname = "ixcsys"

    __lan_hwaddr = None
    __wan_hwaddr = None

    __router_consts = None

    __enable_dhcp_client = None
    __enable_dhcp_server = None

    def init_func(self, debug):
        self.__scgi_fd = -1
        self.__dhcp_fd = -1
        self.__enable_dhcp_client = True
        self.__enable_dhcp_server = False

        global_vars["ixcsys.dhcp"] = self

        if os.path.exists(os.getenv("IXC_MYAPP_SCGI_PATH")): os.remove(os.getenv("IXC_MYAPP_SCGI_PATH"))

        self.create_poll()

        self.start_scgi()
        self.start_dhcp()

    def load_dhcp_configs(self):
        pass

    def save_dhcp_configs(self):
        pass

    def start_dhcp(self):
        self.__dhcp_fd = self.create_handler(-1, dhcp.dhcp_service)
        port = self.get_handler(self.__dhcp_fd).get_sock_port()

        while 1:
            ok = RPCClient.RPCReadyOk("router")
            if not ok:
                time.sleep(5)
            else:
                break

        consts = RPCClient.fn_call("router", "/runtime", "get_all_consts")
        RPCClient.fn_call("router", "/netpkt", "unset_fwd_port", True, consts["IXC_FLAG_DHCP_CLIENT"])
        ok, message = RPCClient.fn_call("router", "/netpkt", "set_fwd_port", True, consts["IXC_FLAG_DHCP_CLIENT"],
                                        port)
        """
        RPCClient.fn_call("router", "/netpkt", "unset_fwd_port", True, consts["IXC_FLAG_DHCP_SERVER"])
        ok, message = RPCClient.fn_call("router", "/netpkt", "set_fwd_port", True, consts["IXC_FLAG_DHCP_SERVER"],
                                        port)
                                        """
        port = RPCClient.fn_call("router", "/netpkt", "get_server_recv_port")

        if not ok:
            raise SystemError(message)
        self.get_handler(self.__dhcp_fd).set_message_auth(message, port)

        _, self.__wan_hwaddr = RPCClient.fn_call("router", "/runtime", "get_wan_hwaddr")
        _, self.__lan_hwaddr = RPCClient.fn_call("router", "/runtime", "get_lan_hwaddr")

        self.__router_consts = consts

        self.__dhcp_server = dhcp_server.dhcp_server(self, self.__hostname, self.__lan_hwaddr, "", "")
        self.__dhcp_client = dhcp_client.dhcp_client(self, self.__hostname, self.__lan_hwaddr)

    def send_dhcp_client_msg(self, msg: bytes):
        if not self.handler_exists(self.__dhcp_fd): return

        self.get_handler(self.__dhcp_fd).send_dhcp_msg(
            self.router_consts["IXC_NETIF_WAN"],
            self.router_consts["IXC_FLAG_DHCP_CLIENT"],
            msg
        )

    def send_dhcp_server_msg(self, msg: bytes):
        if not self.handler_exists(self.__dhcp_fd): return

        self.get_handler(self.__dhcp_fd).send_dhcp_msg(
            self.router_consts["IXC_NETIF_LAN"],
            self.router_consts["IXC_FLAG_DHCP_SERVER"],
            msg
        )

    @property
    def router_consts(self):
        return self.__router_consts

    @property
    def client(self):
        return self.__dhcp_client

    @property
    def server(self):
        return self.__dhcp_server

    @property
    def hostname(self):
        return self.__hostname

    @property
    def wan_hwaddr(self):
        return self.__wan_hwaddr

    @property
    def lan_hwaddr(self):
        return self.__lan_hwaddr

    def start_scgi(self):
        scgi_configs = {
            "use_unix_socket": True,
            "listen": os.getenv("IXC_MYAPP_SCGI_PATH"),
            "application": webroute.app_route()
        }
        self.__scgi_fd = self.create_handler(-1, scgi.scgid_listener, scgi_configs)
        self.get_handler(self.__scgi_fd).after()

    def myloop(self):
        if self.__enable_dhcp_client:
            self.__dhcp_client.loop()
        if self.__enable_dhcp_server:
            self.__dhcp_server.loop()

    def release(self):
        if self.__scgi_fd > 0:
            self.delete_handler(self.__scgi_fd)

        self.__scgi_fd = -1

        if os.path.exists(os.getenv("IXC_MYAPP_SCGI_PATH")): os.remove(os.getenv("IXC_MYAPP_SCGI_PATH"))


def main():
    __helper = "ixc_syscore/netpkt helper: start | stop | debug"
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
