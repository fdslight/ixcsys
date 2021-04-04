# coding=iso-8859-1
# !/usr/bin/env python3
import pickle, os, socket, sys

import router

import ixc_syslib.pylib.logging as logging
import ixc_syscore.router.pylib.pppoe as pppoe

import pywind.lib.netutils as netutils
import pywind.lib.configfile as conf

class rpc(object):
    __fn_objects = None

    def __init__(self, _helper):
        self.__fn_objects = {
            "netif_set_ip": None,
            "netif_get_ip": None,
            "route_add": self.route_add,
            "route_del": None,

        }

    def route_add(self):
        return

    def call(self, fn_name: str, *args, **kwargs):
        """????
        """
        if fn_name not in self.__fn_objects:
            return 0, pickle.dumps("not found function %s" % fn_name)

        fn = self.__fn_objects[fn_name]

        return fn(*args, **kwargs)


class helper(object):
    __WAN_BR_NAME = None
    __LAN_BR_NAME = None

    __LAN_NAME = None
    __WAN_NAME = None

    __router = None
    __debug = None

    __if_lan_fd = None
    __if_wan_fd = None

    __lan_configs = None
    __wan_configs = None
    __router_configs = None
    __port_map_configs = None

    __is_linux = None
    __scgi_fd = None

    __pfwd_fd = None

    __pppoe = None
    __pppoe_enable = None
    __pppoe_user = None
    __pppoe_passwd = None

    __conf_dir = None

    def load_lan_configs(self):
        path = "%s/lan.ini" % self.__conf_dir
        self.__lan_configs = conf.ini_parse_from_file(path)

    def save_lan_configs(self):
        path = "%s/lan.ini" % self.__conf_dir
        conf.save_to_ini(self.__lan_configs, path)

    def load_wan_configs(self):
        path = "%s/wan.ini" % self.__conf_dir
        self.__wan_configs = conf.ini_parse_from_file(path)

    def save_wan_configs(self):
        path = "%s/wan.ini" % self.__conf_dir
        conf.save_to_ini(self.__wan_configs, path)

    def load_router_configs(self):
        path = "%s/router.ini" % self.__conf_dir
        self.__router_configs = conf.ini_parse_from_file(path)

    def load_port_map_configs(self):
        path = "%s/port_map.ini" % self.__conf_dir
        self.__port_map_configs = conf.ini_parse_from_file(path)

    def save_router_configs(self):
        path = "%s/router.ini" % self.__conf_dir
        conf.save_to_ini(self.__router_configs, path)

    def save_port_map_configs(self):
        path = "%s/port_map.ini" % self.__conf_dir
        conf.save_to_ini(self.__port_map_configs, path)

    def reset_port_map(self):
        for name in self.__port_map_configs:
            o = self.__port_map_configs[name]
            protocol = int(o["protocol"])
            port = int(o["port"])
            self.router.port_map_del(protocol, port)
        self.load_port_map_configs()
        for name in self.__port_map_configs:
            o = self.__port_map_configs[name]
            protocol = int(o["protocol"])
            port = int(o["port"])
            address = o["address"]
            self.router.port_map_add(protocol, port, address)

    @property
    def router(self):
        return self.__router

    @property
    def is_linux(self):
        return self.__is_linux

    @property
    def lan_configs(self):
        return self.__lan_configs

    @property
    def wan_configs(self):
        return self.__wan_configs

    @property
    def router_configs(self):
        return self.__router_configs

    @property
    def port_map_configs(self):
        return self.__port_map_configs

    @property
    def debug(self):
        return self.__debug

    @property
    def pppoe_user(self):
        return self.__pppoe_user

    @property
    def pppoe_passwd(self):
        return self.__pppoe_passwd

    def release(self):
        if self.is_linux:
            os.system("ip link set %s down" % self.__LAN_NAME)
            os.system("ip link set %s down" % self.__WAN_NAME)
            os.system("ip link set %s down" % self.__LAN_BR_NAME)
            os.system("ip link set %s down" % self.__WAN_BR_NAME)

            os.system("ip link del %s" % self.__LAN_BR_NAME)
            os.system("ip link del %s" % self.__WAN_BR_NAME)
        else:
            os.system("ifconfig %s destroy" % self.__LAN_BR_NAME)
            os.system("ifconfig %s destroy" % self.__WAN_BR_NAME)

        if self.__if_lan_fd > 0:
            self.router.netif_delete(router.IXC_NETIF_LAN)
        if self.__if_wan_fd > 0:
            self.router.netif_delete(router.IXC_NETIF_WAN)

        self.__if_lan_fd = -1
        self.__if_wan_fd = -1

    def linux_br_create(self, br_name: str, added_bind_ifs: list):
        cmds = [
            "ip link add name %s type bridge" % br_name,
            "ip link set dev %s up" % br_name,
            # "echo 1 >/proc/sys/net/ipv6/conf/all/forwarding",
            # "echo 1 > /proc/sys/net/ipv4/ip_forward"
        ]

        for cmd in cmds: os.system(cmd)
        for if_name in added_bind_ifs:
            cmd = "ip link set dev %s master %s" % (if_name, br_name,)
            os.system(cmd)

    def freebsd_br_create(self, added_bind_ifs: list):
        fd = os.popen("ifconfig bridge create")
        s = fd.read()
        fd.close()
        s = s.replace("\n", "")
        s = s.replace(" ", "")

        _list = ["ifconfig %s" % s, ]
        for name in added_bind_ifs:
            _list.append("addm %s" % name)
        _list.append("up")
        cmd = " ".join(_list)
        os.system(cmd)

        return s

    def start_lan(self):
        self.load_lan_configs()
        lan_ifconfig = self.__lan_configs["if_config"]
        lan_phy_ifname = lan_ifconfig["phy_ifname"]
        hwaddr = lan_ifconfig["hwaddr"]

        self.__if_lan_fd, self.__LAN_NAME = self.__router.netif_create(self.__LAN_NAME, router.IXC_NETIF_LAN)

        self.router.netif_set_hwaddr(router.IXC_NETIF_LAN, netutils.str_hwaddr_to_bytes(hwaddr))

        if self.is_linux:
            self.linux_br_create(self.__LAN_BR_NAME, [lan_phy_ifname, self.__LAN_NAME, ])

            os.system("ip link set %s promisc on" % lan_phy_ifname)
            # os.system("ip link set %s promisc on" % self.__LAN_NAME)
            os.system("ip link set %s up" % lan_phy_ifname)

        else:
            self.__LAN_BR_NAME = self.freebsd_br_create([lan_phy_ifname, self.__LAN_NAME, ])

            os.system("ifconfig %s promisc" % lan_phy_ifname)
            # os.system("ifconfig %s promisc" % self.__WAN_NAME)
            os.system("ifconfig %s up" % lan_phy_ifname)

        lan_addr = lan_ifconfig["ip_addr"]
        manage_addr = lan_ifconfig["manage_addr"]
        mask = lan_ifconfig["mask"]

        byte_ipaddr = socket.inet_pton(socket.AF_INET, lan_addr)
        prefix = netutils.mask_to_prefix(mask, False)

        self.router.netif_set_ip(router.IXC_NETIF_LAN, byte_ipaddr, prefix, False)

        if self.is_linux:
            os.system("ip -4 addr add %s/%s dev %s" % (manage_addr, prefix, self.__LAN_BR_NAME))
            os.system("ip -4 route add default via %s" % lan_addr)

        # IPv6?????
        enable_static_ipv6 = bool(int(lan_ifconfig["enable_static_ipv6"]))
        enable_ipv6_pass = bool(int(lan_ifconfig["enable_ipv6_pass"]))
        enable_ipv6_security = bool(int(lan_ifconfig["enable_ipv6_security"]))
        ip6_addr, v6_prefix = netutils.parse_ip_with_prefix(lan_ifconfig["ip6_addr"])

        byte_ip6addr = socket.inet_pton(socket.AF_INET6, ip6_addr)

        if enable_static_ipv6:
            self.router.netif_set_ip(router.IXC_NETIF_LAN, byte_ip6addr, int(v6_prefix),
                                     True)
        self.router.route_ipv6_pass_enable(enable_ipv6_pass)
        self.router.ip6sec_enable(enable_ipv6_security)
        self.router.g_manage_addr_set(manage_addr, False)

    def start_wan(self):
        self.__pppoe = pppoe.pppoe(self)
        self.load_wan_configs()

        wan_configs = self.__wan_configs
        ip_cfg = wan_configs["ipv4"]

        wan_public = self.__wan_configs["public"]
        wan_phy_ifname = wan_public["phy_ifname"]
        wan_ifhwaddr = wan_public["hwaddr"]
        ipv4 = self.__wan_configs["ipv4"]

        self.__if_wan_fd, self.__WAN_NAME = self.__router.netif_create(self.__WAN_NAME, router.IXC_NETIF_WAN)
        self.router.netif_set_hwaddr(router.IXC_NETIF_WAN, netutils.str_hwaddr_to_bytes(wan_ifhwaddr))

        if self.is_linux:
            self.linux_br_create(self.__WAN_BR_NAME, [wan_phy_ifname, self.__WAN_NAME, ])
            os.system("ip link set %s promisc on" % wan_phy_ifname)
            os.system("ip link set %s promisc on" % self.__WAN_NAME)
            os.system("ip link set %s up" % wan_phy_ifname)
        else:
            pass

        wan_pppoe = self.__wan_configs["pppoe"]
        internet_type = self.__wan_configs["public"]["internet_type"]

        if internet_type == "pppoe":
            self.__pppoe_enable = True
        else:
            self.__pppoe_enable = False

        if self.__pppoe_enable:
            self.__pppoe_user = wan_pppoe["user"]
            self.__pppoe_passwd = wan_pppoe["passwd"]
            self.router.pppoe_enable(True)
            self.router.pppoe_start()
            return

        if internet_type.lower() != "static-ip": return
        # WAN???????

        ip_addr = ipv4["address"]
        mask = ipv4["mask"]
        default_gw = ipv4.get("default_gw", None)

        byte_ipaddr = socket.inet_pton(socket.AF_INET, ip_addr)
        prefix = netutils.mask_to_prefix(mask, 0)

        self.router.netif_set_ip(router.IXC_NETIF_WAN, byte_ipaddr, prefix, False)
        if not default_gw: return

        byte_gw = socket.inet_pton(socket.AF_INET, default_gw)
        byte_subnet = socket.inet_pton(socket.AF_INET, "0.0.0.0")

        self.router.route_add(byte_subnet, 0, byte_gw, False)

    def set_gw_ipaddr(self, ipaddr: str, prefix: int, is_ipv6=False):
        if is_ipv6:
            fa = socket.AF_INET6
        else:
            fa = socket.AF_INET
        byte_ip = socket.inet_pton(fa, ipaddr)

        self.router.netif_set_ip(router.IXC_NETIF_LAN, byte_ip, prefix, False)

    def get_manage_addr(self):
        return self.lan_configs["if_config"]["manage_addr"]

    def set_router(self):
        """????????
        :return:
        """
        self.load_router_configs()
        # ???QOS????
        qos = self.__router_configs["qos"]
        udp_udplite_first = bool(int(qos["udp_udplite_first"]))
        self.router.qos_udp_udplite_first_enable(udp_udplite_first)

    def port_map_add(self, protocol: int, port: int, address: str, alias_name: str):
        self.__port_map_configs[alias_name] = {
            "protocol": protocol,
            "port": port,
            "address": address
        }
        self.save_port_map_configs()
        self.reset_port_map()

    def port_map_del(self, protocol: int, port: int):
        alias_name = None
        for name in self.__port_map_configs:
            o = self.__port_map_configs[name]
            p = int(o["protocol"])
            _port = int(o["port"])
            if p == protocol and _port == port:
                alias_name = name
                break
            ''''''
        if alias_name: del self.__port_map_configs[alias_name]
        self.save_port_map_configs()
        self.reset_port_map()

    def __init__(self, debug: bool):
        self.__conf_dir = "%s/../../ixc_configs/router" % os.path.dirname(__file__)
        self.__debug = debug
        self.__router = router.router()
        self.__if_lan_fd = -1
        self.__if_wan_fd = -1

        self.__WAN_BR_NAME = "ixcwanbr"
        self.__LAN_BR_NAME = "ixclanbr"

        self.__LAN_NAME = "ixclan"
        self.__WAN_NAME = "ixcwan"

        self.__wan_configs = {}
        self.__is_linux = sys.platform.startswith("linux")

        # ????FreeBSD?????if_tap.ko??
        if not self.is_linux:
            fd = os.popen("kldstat")
            s = fd.read()
            fd.close()
            p = s.find("if_tap.ko")
            if p < 0: os.system("kldload if_tap")

        self.start_lan()
        # ??start_wan????
        self.start_wan()

        # self.set_router()

        # self.load_port_map_configs()
        # self.reset_port_map()

    @property
    def router(self):
        return self.__router

    def pppoe_session_handle(self, protocol: int, byte_data: bytes):
        """?????C???PPPoE????
        """
        self.__pppoe.handle_packet_from_ns(protocol, byte_data)

    @property
    def pppoe_user(self):
        return self.__pppoe_user

    @property
    def pppoe_passwd(self):
        return self.__pppoe_passwd

    def rpc_fn_call(self, name: str, arg_data: bytes):
        """C?????????RPC
        :return (is_error,byte_message)
        """
        return 0, b"hello,world"

    def tell(self, cmd: str, *args):
        """C???Python?????
        """
        if cmd == "lcp_start":
            if self.__pppoe: self.__pppoe.start_lcp()
        if cmd == "lcp_stop":
            if self.__pppoe: self.__pppoe.stop_lcp()

    def loop(self):
        """C???????????????
        """
        self.__pppoe.loop()