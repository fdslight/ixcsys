#!/usr/bin/env python3
import sys, os, signal, time

sys.path.append(os.getenv("IXC_SYS_DIR"))

if not os.path.isdir(os.getenv("IXC_MYAPP_TMP_DIR")): os.mkdir(os.getenv("IXC_MYAPP_TMP_DIR"))

import pywind.evtframework.evt_dispatcher as dispatcher
import pywind.lib.proc as proc
import pywind.lib.configfile as conf
import pywind.web.handlers.scgi as scgi
import pywind.lib.netutils as netutils

from pywind.global_vars import global_vars

import ixc_syscore.DHCP.handlers.dhcpd as dhcp
import ixc_syscore.DHCP.pylib.dhcp_client as dhcp_client
import ixc_syscore.DHCP.pylib.dhcp_server as dhcp_server
import ixc_syscore.DHCP.pylib.netpkt as netpkt

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
    __router_lan_configs = None
    __router_wan_configs = None

    __positive_dhcp_client_req = None

    # MAC地址表厂家映射
    __oui_map = None
    # oui文件路径
    __oui_fpath = None

    def init_func(self, debug):
        self.__debug = debug
        self.__scgi_fd = -1
        self.__dhcp_fd = -1
        self.__rand_key = os.urandom(16)
        self.__dhcp_ip_bind = {}

        self.__dhcp_server_conf_path = "%s/dhcp_server.ini" % os.getenv("IXC_MYAPP_CONF_DIR")
        self.__dhcp_ip_bind_path = "%s/ip_bind.ini" % os.getenv("IXC_MYAPP_CONF_DIR")

        self.__oui_map = {}
        self.__oui_fpath = "%s/data/oui.txt" % os.getenv("IXC_MYAPP_DIR")

        global_vars["ixcsys.DHCP"] = self

        # if os.path.exists(os.getenv("IXC_MYAPP_SCGI_PATH")): os.remove(os.getenv("IXC_MYAPP_SCGI_PATH"))

        RPCClient.wait_processes(["router", "DNS"])

        self.load_dhcp_server_configs()
        self.load_dhcp_server_ip_bind()

        if not os.path.isfile(self.__oui_fpath):
            self.__oui_map = self.parse_oui(self.__oui_fpath)

        self.create_poll()

        self.start_dhcp()
        self.start_scgi()

    def load_dhcp_server_configs(self):
        self.__dhcp_server_configs = conf.ini_parse_from_file(self.__dhcp_server_conf_path)
        if "lease_time" not in self.__dhcp_server_configs["public"]:
            self.__dhcp_server_configs["public"]["lease_time"] = 600

    def load_dhcp_server_ip_bind(self):
        self.__dhcp_ip_bind = conf.ini_parse_from_file(self.__dhcp_ip_bind_path)

    def save_dhcp_server_configs(self):
        conf.save_to_ini(self.__dhcp_server_configs, self.__dhcp_server_conf_path)

    def save_ip_bind_configs(self):
        conf.save_to_ini(self.__dhcp_ip_bind, self.__dhcp_ip_bind_path)

    @property
    def conf_dir(self):
        return os.getenv("IXC_MYAPP_CONF_DIR")

    @property
    def server_configs(self):
        return self.__dhcp_server_configs

    @property
    def positive_dhcp_client_request(self):
        return self.__positive_dhcp_client_req

    def start_dhcp_client(self, port: int):
        self.__dhcp_client = dhcp_client.dhcp_client(self, self.__hostname, self.__lan_hwaddr)
        consts = self.__router_consts

        RPCClient.fn_call("router", "/config", "unset_fwd_port", consts["IXC_FLAG_DHCP_CLIENT"])
        ok, message = RPCClient.fn_call("router", "/config", "set_fwd_port", consts["IXC_FLAG_DHCP_CLIENT"],
                                        self.__rand_key, port)

        wan_config = RPCClient.fn_call("router", "/config", "wan_config_get")
        self.__positive_dhcp_client_req = bool(int(wan_config["dhcp"]["positive_heartbeat"]))

        if not ok: raise SystemError(message)

    def start_dhcp_server(self, port: int):
        consts = self.__router_consts
        public = self.__dhcp_server_configs["public"]

        addr_begin = public["range_begin"]
        addr_end = public["range_end"]
        lease_time = int(self.__dhcp_server_configs["public"]["lease_time"])

        if_config = self.__router_lan_configs["if_config"]
        gw_addr = if_config["ip_addr"]
        mask = if_config["mask"]
        prefix = netutils.mask_to_prefix(mask, is_ipv6=False)
        subnet = netutils.calc_subnet(gw_addr, prefix, is_ipv6=False)

        self.__manage_addr = if_config["manage_addr"]

        self.__dhcp_server = dhcp_server.dhcp_server(
            self, gw_addr, self.__hostname, self.__lan_hwaddr, addr_begin, addr_end,
            subnet, int(prefix)
        )

        RPCClient.fn_call("router", "/config", "unset_fwd_port", consts["IXC_FLAG_DHCP_SERVER"])
        ok, message = RPCClient.fn_call("router", "/config", "set_fwd_port", consts["IXC_FLAG_DHCP_SERVER"],
                                        self.__rand_key, port)
        if not ok: raise SystemError(message)

        self.__dhcp_server.load_dhcp_cache()
        self.__dhcp_server.set_timeout(lease_time)

    def start_dhcp(self):
        self.__dhcp_fd = self.create_handler(-1, dhcp.dhcp_service)
        dhcp_msg_port = self.get_handler(self.__dhcp_fd).get_sock_port()

        if self.debug: print("start DHCP")

        self.get_handler(self.__dhcp_fd).set_message_auth(self.__rand_key)
        consts = RPCClient.fn_call("router", "/config", "get_all_consts")
        self.__router_consts = consts

        lan_configs = RPCClient.fn_call("router", "/config", "lan_config_get")
        self.__router_lan_configs = lan_configs

        wan_configs = RPCClient.fn_call("router", "/config", "wan_config_get")
        self.__router_wan_configs = wan_configs

        self.__lan_hwaddr = lan_configs["if_config"]["hwaddr"]
        self.__wan_hwaddr = wan_configs["public"]["hwaddr"]

        self.start_dhcp_client(dhcp_msg_port)
        self.start_dhcp_server(dhcp_msg_port)

    def start_scgi(self):
        scgi_configs = {
            "use_unix_socket": True,
            "listen": os.getenv("IXC_MYAPP_SCGI_PATH"),
            "application": webroute.app_route()
        }
        self.__scgi_fd = self.create_handler(-1, scgi.scgid_listener, scgi_configs)
        self.get_handler(self.__scgi_fd).after()

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
    def dhcp_client_enable(self):
        wan_pub = self.__router_wan_configs["public"]
        if wan_pub["internet_type"] != "dhcp": return False
        return True

    @property
    def dhcp_server_enable(self):
        conf_pub = self.__dhcp_server_configs["public"]
        enable = bool(int(conf_pub["enable"]))
        return enable

    @property
    def dhcp_ip_bind(self):
        return self.__dhcp_ip_bind

    @property
    def server(self):
        return self.__dhcp_server

    @property
    def manage_addr(self):
        return self.__manage_addr

    @property
    def oui_map(self):
        return self.__oui_map

    def handle_arp_data(self, link_data: bytes):
        """处理ARP数据包
        """
        dst_hwaddr, src_hwaddr, link_proto, arp_data = netpkt.parse_ether_data(link_data)
        arp_info = netpkt.arp_parse(arp_data)
        if not arp_info: return
        # 只处理ARP响应,ARP主要应用于检查IP地址是否冲突
        if arp_info[0] != 2: return

        if self.dhcp_server_enable: self.server.handle_arp(dst_hwaddr, src_hwaddr, arp_info)
        if self.dhcp_client_enable: self.client.handle_arp(dst_hwaddr, src_hwaddr, arp_info)

    def send_arp_request(self, my_hwaddr: bytes, my_ipaddr: bytes, dst_addr=None, is_server=False):
        """发送ARP请求验证IP地址冲突
        """
        if not dst_addr:
            dst_addr = my_ipaddr
        link_brd = bytes([0xff, 0xff, 0xff, 0xff, 0xff, 0xff])
        arp_data = netpkt.arp_build(1, my_hwaddr, link_brd, my_ipaddr, dst_addr)
        link_data = netpkt.build_ether_data(link_brd, my_hwaddr, 0x806, arp_data)

        if is_server:
            self.send_dhcp_server_msg(link_data)
        else:
            self.send_dhcp_client_msg(link_data)

    def set_wan_ip(self, ip: str, prefix: int, is_ipv6=False):
        """设置WAN口的IP地址
        """
        rs = RPCClient.fn_call("router", "/config", "set_wan_ipaddr", ip, prefix, is_ipv6=is_ipv6)
        ok, msg = rs
        if not ok: logging.print_error(msg)

        return ok

    def set_nameservers(self, ns1: str, ns2: str, is_ipv6=False):
        rs = RPCClient.fn_call("DNS", "/config", "set_nameservers", ns1, ns2, is_ipv6=is_ipv6)

    def set_default_route(self, gw: str, is_ipv6=False):
        if is_ipv6:
            # 首先删除默认路由
            RPCClient.fn_call("router", "/config", "del_route", "::", 0, is_ipv6=True)
            rs = RPCClient.fn_call("router", "/config", "add_route", "::", 0, gw, is_ipv6=True)
        else:
            # 首先删除默认路由
            RPCClient.fn_call("router", "/config", "del_route", "0.0.0.0", 0, is_ipv6=False)
            rs = RPCClient.fn_call("router", "/config", "add_route", "0.0.0.0", 0, gw, is_ipv6=False)

        ok, msg = rs
        if not ok: logging.print_error(msg)
        return ok

    @property
    def hostname(self):
        return self.__hostname

    @property
    def wan_hwaddr(self):
        return self.__wan_hwaddr

    @property
    def lan_hwaddr(self):
        return self.__lan_hwaddr

    @property
    def debug(self):
        return self.__debug

    def __parse_oui_corp(self, s: bytes):
        """解析厂商
        """
        _list = s.split(b"\r\n")
        if not _list: return None
        ss = _list.pop(0).decode()
        p = ss.find("(hex)")
        prefix = ss[0:p].strip().replace("\t", "")
        p += 5
        corp = ss[p:].strip().replace("\t", "")

        return prefix, corp

    def parse_oui(self, path: str):
        """解析MAC OUI文件
        """
        fdst = open(path, "rb")

        s = fdst.read()
        fdst.close()

        _list = []

        # 首先提取每个厂商部分
        while 1:
            p = s.find(b"\r\n\r\n")
            if p < 4: break
            _list.append(s[0:p])
            p += 4
            s = s[p:]
        if _list: _list.pop(0)

        results = {}

        for s in _list:
            result = self.__parse_oui_corp(s)
            if not result: continue
            k, v = result
            results[k] = v
        return results

    def myloop(self):
        if self.dhcp_client_enable: self.client.loop()
        if self.dhcp_server_enable: self.server.loop()

    def release(self):
        if self.__scgi_fd > 0:
            self.delete_handler(self.__scgi_fd)
        self.__scgi_fd = -1
        if os.path.exists(os.getenv("IXC_MYAPP_SCGI_PATH")): os.remove(os.getenv("IXC_MYAPP_SCGI_PATH"))
        if self.__dhcp_server: self.__dhcp_server.save_dhcp_cache()


def main():
    __helper = "ixc_syscore/DHCP helper: start | stop | debug"
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
