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

import ixc_syscore.PASS.handlers.TrafficPass as TrafficPass
import ixc_syscore.PASS.handlers.forward as forward

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
    __pass_fd = None
    __forward_fd = None
    __router_consts = None

    __server_port = None
    __rand_key = None

    __debug = None
    __manage_addr = None
    __conf_path = None
    # 是否开启了直通功能
    __enable_pass_flags = None
    __configs = None

    def init_func(self, debug):
        self.__debug = debug
        self.__scgi_fd = -1
        self.__pass_fd = -1
        self.__forward_fd = -1
        self.__rand_key = os.urandom(16)
        self.__enable_pass_flags = False

        self.__conf_path = "%s/pass.ini" % os.getenv("IXC_MYAPP_CONF_DIR")

        global_vars["ixcsys.PASS"] = self

        if os.path.exists(os.getenv("IXC_MYAPP_SCGI_PATH")): os.remove(os.getenv("IXC_MYAPP_SCGI_PATH"))

        RPCClient.wait_processes(["router", ])
        time.sleep(5)
        self.load_configs()

        self.create_poll()

        self.start_pass()
        self.start_scgi()

    def send_message_to_router(self, message: bytes):
        if self.__pass_fd < 0: return
        self.get_handler(self.__pass_fd).send_msg(message)

    @property
    def conf_dir(self):
        return os.getenv("IXC_MYAPP_CONF_DIR")

    def load_configs(self):
        self.__configs = conf.ini_parse_from_file(self.__conf_path)

    def change_pass(self):
        enable = bool(int(self.__configs['config']['enable']))
        self.disable_pass()
        if enable: self.enable_pass()

    def save_configs(self):
        self.change_pass()
        conf.save_to_ini(self.__configs, self.__conf_path)

    @property
    def configs(self):
        return self.__configs

    def start_pass(self):
        consts = RPCClient.fn_call("router", "/config", "get_all_consts")
        self.__router_consts = consts

        lan_configs = RPCClient.fn_call("router", "/config", "lan_config_get")
        if_config = lan_configs["if_config"]
        self.__manage_addr = if_config["manage_addr"]

        self.__pass_fd = self.create_handler(-1, TrafficPass.pass_service)
        port = self.get_handler(self.__pass_fd).get_sock_port()

        RPCClient.fn_call("router", "/config", "unset_fwd_port", consts["IXC_FLAG_ETHER_PASS"])
        ok, message = RPCClient.fn_call("router", "/config", "set_fwd_port", consts["IXC_FLAG_ETHER_PASS"],
                                        self.__rand_key, port)

        self.get_handler(self.__pass_fd).set_message_auth(self.__rand_key)
        self.__forward_fd = self.create_handler(-1, forward.forward_handler)
        self.change_pass()

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

    @property
    def router_consts(self):
        return self.__router_consts

    def enable_pass(self):
        ifname = "eth3"
        RPCClient.fn_call("router", "/config", "start_pass", ifname)

    def disable_pass(self):
        RPCClient.fn_call("router", "/config", "stop_pass")

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
