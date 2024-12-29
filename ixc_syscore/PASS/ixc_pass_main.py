#!/usr/bin/env python3
import hashlib
import socket
import sys, os, signal, time

sys.path.append(os.getenv("IXC_SYS_DIR"))

if not os.path.isdir(os.getenv("IXC_MYAPP_TMP_DIR")): os.mkdir(os.getenv("IXC_MYAPP_TMP_DIR"))

import pywind.evtframework.evt_dispatcher as dispatcher
import pywind.lib.proc as proc
import pywind.lib.configfile as conf
import pywind.web.handlers.scgi as scgi
import pywind.lib.netutils as netutils
from pywind.global_vars import global_vars

import ixc_syslib.pylib.logging as logging
import ixc_syslib.pylib.RPCClient as RPCClient
import ixc_syslib.web.route as webroute
import ixc_syslib.pylib.osnet as osnet

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
    __router_consts = None
    __debug = None
    __conf_path = None
    __configs = None

    __peer_ipaddr = None
    __up_time = None

    def init_func(self, debug):
        self.__debug = debug
        self.__scgi_fd = -1
        self.__up_time = time.time()

        self.__conf_path = "%s/pass.ini" % os.getenv("IXC_MYAPP_CONF_DIR")

        global_vars["ixcsys.PASS"] = self

        if os.path.exists(os.getenv("IXC_MYAPP_SCGI_PATH")): os.remove(os.getenv("IXC_MYAPP_SCGI_PATH"))

        RPCClient.wait_processes(["router", ])
        time.sleep(5)
        self.load_configs()

        self.create_poll()

        self.start_pass()
        self.start_scgi()

    @property
    def conf_dir(self):
        return os.getenv("IXC_MYAPP_CONF_DIR")

    def load_configs(self):
        self.__configs = conf.ini_parse_from_file(self.__conf_path)
        myconf = self.__configs["config"]
        if "key" not in myconf:
            myconf["key"] = "key"
        if "peer_host" not in myconf:
            myconf["peer_host"] = "www.example.com"
        if "peer_port" not in myconf:
            myconf["peer_port"] = 8964

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

    def get_peer_address(self):
        myconf = self.configs["config"]
        peer_host = myconf.get("peer_host", "")

        if netutils.is_ipv6_address(peer_host): return ""
        if netutils.is_ipv4_address(peer_host): return peer_host

        try:
            ipaddr = socket.gethostbyname(peer_host)
        except:
            return ""
        # 获取地址
        return ipaddr

    def start_pass(self):
        self.reset_pass_address()
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
    def debug(self):
        return self.__debug

    @property
    def router_consts(self):
        return self.__router_consts

    def enable_pass(self):
        ifname = self.configs['config']['if_name']
        if_devs = osnet.get_if_net_devices()
        if ifname not in if_devs:
            logging.print_error("cannot found PASS NIC %s" % ifname)
            return
        RPCClient.fn_call("router", "/config", "start_pass", ifname)

    def disable_pass(self):
        RPCClient.fn_call("router", "/config", "stop_pass")

    @property
    def device(self):
        return self.get_handler(self.__forward_fd).device

    def myloop(self):
        self.update_peer_address()

    def reset_pass_address(self):
        consts = RPCClient.fn_call("router", "/config", "get_all_consts")
        self.__router_consts = consts

        myconf = self.configs["config"]
        key = myconf.get("key", "key").encode()
        md5 = hashlib.md5()
        md5.update(key)
        rand_key = md5.digest()

        try:
            port = int(myconf.get("peer_port", "8964"))
        except ValueError:
            port = 8964

        if port < 1 or port >= 65536:
            port = 8964

        RPCClient.fn_call("router", "/config", "unset_fwd_port", consts["IXC_FLAG_ETHER_PASS"])

        peer_address = self.get_peer_address()
        if not peer_address:
            logging.print_error("cannot find the peer address or peer address error")
            return

        self.__peer_ipaddr = peer_address
        ok, message = RPCClient.fn_call("router", "/config", "set_fwd_port", consts["IXC_FLAG_ETHER_PASS"],
                                        rand_key, port, address=peer_address)

    def update_peer_address(self):
        enable = bool(int(self.__configs['config']['enable']))

        now = time.time()
        if now - self.__up_time >= 0 or now - self.__up_time < 60:
            return

        if not enable: return

        peer_addr = self.get_peer_address()
        if peer_addr == "": return
        if peer_addr != self.__peer_ipaddr:
            self.reset_pass_address()
        self.__peer_ipaddr = peer_addr

    def release(self):
        self.disable_pass()
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
