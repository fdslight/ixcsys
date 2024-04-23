#!/usr/bin/env python3
import sys, os, signal, time

sys.path.append(os.getenv("IXC_SYS_DIR"))

if not os.path.isdir(os.getenv("IXC_MYAPP_TMP_DIR")): os.mkdir(os.getenv("IXC_MYAPP_TMP_DIR"))

import pywind.evtframework.evt_dispatcher as dispatcher
import pywind.lib.proc as proc
import pywind.lib.configfile as conf
import pywind.web.handlers.scgi as scgi
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
        logging.print_error(debug=debug)

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

    __dhcp_server_conf_path = None
    __dhcp_ip_bind_path = None

    __dhcp_client_configs = None
    __dhcp_server_configs = None
    __dhcp_ip_bind = None

    __server_port = None
    __rand_key = None

    __debug = None
    __manage_addr = None


    def init_func(self, debug):
        self.__debug = debug
        self.__scgi_fd = -1
        self.__pass_fd = -1
        self.__forward_fd = -1
        self.__rand_key = os.urandom(16)

        self.__dhcp_server_conf_path = "%s/pass.ini" % os.getenv("IXC_MYAPP_CONF_DIR")

        global_vars["ixcsys.PASS"] = self

        # if os.path.exists(os.getenv("IXC_MYAPP_SCGI_PATH")): os.remove(os.getenv("IXC_MYAPP_SCGI_PATH"))

        RPCClient.wait_processes(["router", "DNS", ])
        time.sleep(5)

        self.create_poll()

        self.start_pass()
        self.start_scgi()

    @property
    def conf_dir(self):
        return os.getenv("IXC_MYAPP_CONF_DIR")

    @property
    def configs(self):
        return {}

    def start_pass(self):
        pass

    def start_scgi(self):
        scgi_configs = {
            "use_unix_socket": True,
            "listen": os.getenv("IXC_MYAPP_SCGI_PATH"),
            "application": webroute.app_route()
        }
        self.__scgi_fd = self.create_handler(-1, scgi.scgid_listener, scgi_configs)
        self.get_handler(self.__scgi_fd).after()

    @property
    def manage_addr(self):
        return self.__manage_addr

    @property
    def debug(self):
        return self.__debug

    def myloop(self):
        pass

    def release(self):
        if self.__scgi_fd > 0:
            self.delete_handler(self.__scgi_fd)
        self.__scgi_fd = -1
        if os.path.exists(os.getenv("IXC_MYAPP_SCGI_PATH")): os.remove(os.getenv("IXC_MYAPP_SCGI_PATH"))


def main():
    __helper = "ixc_syscore/PASS helper: start | stop | debug"
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
