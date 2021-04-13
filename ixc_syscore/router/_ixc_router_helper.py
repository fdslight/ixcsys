# !/usr/bin/env python3
import pickle, os, socket, sys, gc

import router

import ixc_syscore.router.pylib.pppoe as pppoe

import ixc_syslib.pylib.RPCClient as RPC
import pywind.lib.netutils as netutils
import pywind.lib.configfile as conf


class rpc(object):
    __fn_objects = None
    __helper = None

    def __init__(self, _helper):
        self.__helper = _helper

        self.__fn_objects = {
            "get_all_consts": self.get_all_consts,
            "get_wan_ipaddr_info": self.get_wan_ipaddr_info,
            "get_lan_ipaddr_info": self.get_lan_ipaddr_info,
            "add_route": self.add_route,
            "del_route": self.del_route,
            "set_wan_ipaddr": self.set_wan_ipaddr,
            "wan_ready_ok": self.wan_ready_ok,
            "vsw_enable": self.vsw_enable,

            "set_fwd_port": self.set_fwd_port,
            "unset_fwd_port": self.unset_fwd_port,

            "wan_config_get": self.wan_config_get,
            "lan_config_get": self.lan_config_get,
            "manage_addr_get": self.manage_addr_get,
            "wan_hwaddr_set": self.wan_hwaddr_set,
            "wan_addr_set": self.wan_addr_set,
            "cur_internet_type_get": self.cur_internet_type_get,
            "internet_type_set": self.internet_type_set,
            "dhcp_positive_heartbeat_set": self.dhcp_positive_heartbeat_set,
            "lan_ipv6_pass_enable": self.lan_ipv6_pass_enable,
            "lan_static_ipv6_enable": self.lan_static_ipv6_enable,
            "lan_static_ipv6_set": self.lan_static_ipv6_set,
            "lan_ipv6_security_enable": self.lan_ipv6_security_enable,
            "pppoe_set": self.pppoe_set,
            "router_config_get": self.router_config_get,
            "qos_set_udp_udplite_first": self.qos_set_udp_udplite_first,
            "port_map_add": self.port_map_add,
            "port_map_del": self.port_map_del,
            "port_map_configs_get": self.port_map_configs_get,
            "src_filter_set_ip": self.src_filter_set_ip,
            "src_filter_enable": self.src_filter_enable,
            "src_filter_set_protocols": self.src_filter_set_protocols,
            "config_save": self.save
        }

    def call(self, fn_name: str, *args, **kwargs):
        """调用函数
        """
        if fn_name not in self.__fn_objects:
            return 0, pickle.dumps("not found function %s" % fn_name)
        fn = self.__fn_objects[fn_name]

        is_error, msg = fn(*args, **kwargs)

        return is_error, pickle.dumps(msg)

    def get_all_consts(self):
        """获取所有转发数据包的flags
        :return:
        """
        values = {
            "IXC_FLAG_DHCP_CLIENT": router.IXC_FLAG_DHCP_CLIENT,
            "IXC_FLAG_DHCP_SERVER": router.IXC_FLAG_DHCP_SERVER,
            "IXC_FLAG_ARP": router.IXC_FLAG_ARP,
            "IXC_FLAG_VSWITCH": router.IXC_FLAG_VSWITCH,
            "IXC_FLAG_SRC_FILTER": router.IXC_FLAG_SRC_FILTER,
            "IXC_FLAG_ROUTE_FWD": router.IXC_FLAG_ROUTE_FWD,
            "IXC_NETIF_LAN": router.IXC_NETIF_LAN,
            "IXC_NETIF_WAN": router.IXC_NETIF_WAN,
        }

        return 0, values

    def get_wan_hwaddr(self):
        """获取WAN硬件地址
        :return:
        """
        wan_configs = self.__helper.wan_configs
        public = wan_configs["public"]

        return 0, (public["phy_ifname"], public["hwaddr"],)

    def get_gw_hwaddr(self):
        """获取LAN硬件地址
        :return:
        """
        if_config = self.__helper.lan_configs["if_config"]
        return 0, (if_config["phy_ifname"], if_config["hwaddr"],)

    def get_wan_ipaddr_info(self, is_ipv6=False):
        return 0, self.__helper.router.netif_get_ip(router.IXC_NETIF_WAN, is_ipv6)

    def get_lan_ipaddr_info(self, is_ipv6=False):
        return 0, self.__helper.router.netif_get_ip(router.IXC_NETIF_LAN, is_ipv6)

    def check_ipaddr_args(self, ipaddr: str, prefix: int, is_ipv6=False):
        if is_ipv6 and not netutils.is_ipv6_address(ipaddr):
            return False, "wrong IPv6 address format"
        if not is_ipv6 and not netutils.is_ipv4_address(ipaddr):
            return False, "wrong IP address format"
        try:
            prefix = int(prefix)
        except ValueError:
            return False, "wrong prefix value %s" % prefix

        if prefix < 0:
            return False, "wrong prefix value %d" % prefix
        if is_ipv6 and prefix > 128:
            return False, "wrong IPv6 prefix value %d" % prefix
        if not is_ipv6 and prefix > 32:
            return False, "wrong IP prefix value %d" % prefix

        return True, ""

    def set_gw_ipaddr(self, ipaddr: str, prefix: int, is_ipv6=False):
        """设置网关的IP地址
        """
        prefix = int(prefix)
        check_ok, err_msg = self.check_ipaddr_args(ipaddr, prefix, is_ipv6=is_ipv6)
        if not check_ok:
            return 0, (check_ok, err_msg,)

        if is_ipv6:
            fa = socket.AF_INET6
        else:
            fa = socket.AF_INET
        byte_ip = socket.inet_pton(fa, ipaddr)
        set_ok = self.__helper.router.netif_set_ip(router.IXC_NETIF_LAN, byte_ip, prefix, is_ipv6)

        return 0, (set_ok, "")

    def set_manage_ipaddr(self, ipaddr: str, is_ipv6=False, is_local=False):
        """设置管理地址
        """
        self.__helper.set_manage_ipaddr(ipaddr, is_ipv6=is_ipv6, is_local=is_local)
        return 0, None

    def get_manage_ipaddr(self):
        """获取管理地址
        """
        ipaddr = self.__helper.get_manage_addr()

        return 0, ipaddr

    def get_lan_configs(self):
        return 0, self.__helper.lan_configs

    def get_wan_configs(self):
        return 0, self.__helper.wan_configs

    def set_wan_ipaddr(self, ipaddr: str, prefix: int, is_ipv6=False):
        """设置WAN口的IP地址
        """
        check_ok, err_msg = self.check_ipaddr_args(ipaddr, int(prefix), is_ipv6=is_ipv6)
        if not check_ok:
            return 0, (check_ok, err_msg,)

        if self.__helper.router.pppoe_is_enabled():
            return 0, (False, "PPPoE is enabled,cannot set wan IP or IPv6 address")

        if is_ipv6:
            fa = socket.AF_INET6
        else:
            fa = socket.AF_INET
        byte_ip = socket.inet_pton(fa, ipaddr)
        set_ok = self.__helper.router.netif_set_ip(router.IXC_NETIF_WAN, byte_ip, prefix, is_ipv6)

        return 0, (set_ok, "")

    def add_route(self, subnet: str, prefix: int, gw: str, is_ipv6=False):
        if is_ipv6 and (not netutils.is_ipv6_address(subnet) or not netutils.is_ipv6_address(gw)):
            return 0, (False, "Wrong subnet or gateway address format for IPv6")

        if not is_ipv6 and (not netutils.is_ipv4_address(subnet) or not netutils.is_ipv4_address(gw)):
            return 0, (False, "Wrong subnet or gateway address format for IP")

        if prefix < 0:
            return 0, (False, "Wrong prefix value %d" % prefix)

        if is_ipv6 and prefix > 128:
            return 0, (False, "Wrong prefix value %d" % prefix)

        if not is_ipv6 and prefix > 32:
            return 0, (False, "Wrong prefix value %d" % prefix)

        if is_ipv6:
            fa = socket.AF_INET6
        else:
            fa = socket.AF_INET

        byte_subnet = socket.inet_pton(fa, subnet)
        byte_gw = socket.inet_pton(fa, gw)

        rs = self.__helper.router.route_add(byte_subnet, prefix, byte_gw, is_ipv6)

        return 0, (rs, "")

    def del_route(self, subnet: str, prefix: int, is_ipv6=False):
        ok, mesg = self.check_ipaddr_args(subnet, prefix, is_ipv6=is_ipv6)

        if not ok: return 0, (ok, mesg)

        if is_ipv6:
            fa = socket.AF_INET6
        else:
            fa = socket.AF_INET

        byte_subnet = socket.inet_pton(fa, subnet)
        self.__helper.router.route_del(byte_subnet, prefix, is_ipv6)

        return 0, (True, "")

    def pppoe_is_enabled(self):
        is_enabled = self.__helper.router.pppoe_is_enabled()

        return 0, is_enabled

    def wan_ready_ok(self):
        return 0, self.__helper.router.wan_ready_ok()

    def vsw_enable(self, enable: bool):
        """开启或者关闭虚拟交换
        :param enable:
        :return:
        """
        return 0, self.__helper.router.vsw_enable(enable)

    def set_fwd_port(self, flags: int, _id: bytes, fwd_port: int):
        if not isinstance(_id, bytes):
            return 0, (False, "Wrong _id data type")
        if len(_id) != 16:
            return 0, (False, "Wrong _id length")
        try:
            fwd_port = int(fwd_port)
        except ValueError:
            return 0, (False, "Wrong fwd_port data type")

        if fwd_port > 0xfffe or fwd_port < 1:
            return 0, (False, "Wrong fwd_port value")

        try:
            flags = int(flags)
        except ValueError:
            return RPC.ERR_ARGS, "wrong flags value type"

        rs = self.__helper.router.netpkt_forward_set(_id, fwd_port, flags)

        return 0, (rs, "")

    def unset_fwd_port(self, flags: int):
        try:
            flags = int(flags)
        except ValueError:
            return RPC.ERR_ARGS, "wrong argument type"
        self.__helper.router.netpkt_forward_disable(flags)
        return 0, None

    def wan_config_get(self):
        return 0, self.__helper.wan_configs

    def lan_config_get(self):
        return 0, self.__helper.lan_configs

    def manage_addr_get(self):
        lan_configs = self.__helper.lan_configs

        return 0, lan_configs["if_config"]["manage_addr"]

    def wan_hwaddr_set(self, hwaddr: str):
        if not netutils.is_hwaddr(hwaddr):
            return RPC.ERR_ARGS, "wrong hwaddr format"

        configs = self.__helper.wan_configs
        configs["public"]["hwaddr"] = hwaddr

        return 0, None

    def cur_internet_type_get(self):
        """获取当前internet上网方式
        """
        wan_configs = self.__helper.wan_configs
        public = wan_configs["public"]

        return 0, public["internet_type"]

    def pppoe_set(self, username: str, passwd: str, heartbeat=False):
        if not username or not passwd:
            return RPC.ERR_ARGS, "empty username or password"
        configs = self.__helper.wan_configs
        pppoe = configs["pppoe"]

        pppoe["user"] = username
        pppoe["passwd"] = passwd

        if heartbeat:
            pppoe["heartbeat"] = 1
        else:
            pppoe["heartbeat"] = 0

        return 0, None

    def internet_type_set(self, _type: str):
        types = (
            "pppoe", "dhcp", "static-ip",
        )
        if _type not in types:
            return RPC.ERR_ARGS, "wrong internet type value,there is pppoe,dhcp or static-ip"

        public = self.__helper.wan_configs["public"]
        public["internet_type"] = _type

        return 0, None

    def wan_addr_set(self, ip: str, mask: str, gw: str):
        if not netutils.is_ipv4_address(ip) or not netutils.is_mask(mask) or not netutils.is_ipv4_address(gw):
            return RPC.ERR_ARGS, "wrong argument value format"

        prefix = netutils.mask_to_prefix(mask, is_ipv6=False)
        if not netutils.is_same_network(ip, gw, prefix, is_ipv6=False):
            return RPC.ERR_ARGS, "wrong argument value"

        ipv4 = self.__helper.wan_configs["ipv4"]
        ipv4["address"] = ip
        ipv4["mask"] = mask
        ipv4["default_gw"] = gw

        return 0, None

    def lan_static_ipv6_set(self, subnet: str, prefix: int):
        if not netutils.is_ipv6_address(subnet):
            return RPC.ERR_ARGS, "wrong IPv6 addres value"
        try:
            int(prefix)
        except ValueError:
            return RPC.ERR_ARGS, "wrong prefix value type"

        prefix = int(prefix)
        if prefix < 48 or prefix > 64:
            return RPC.ERR_ARGS, "prefix value must be 48 to 64"

        configs = self.__helper.lan_configs["if_config"]
        configs["ip6_addr"] = "%s/%s" % (subnet, prefix,)

        return 0, None

    def lan_static_ipv6_enable(self, enable: bool):
        """是否开启静态IPv6地址
        """
        configs = self.__helper.lan_configs["if_config"]
        if enable:
            configs["enable_static_ipv6"] = 1
        else:
            configs["enable_static_ipv6"] = 0

        return 0, None

    def lan_ipv6_pass_enable(self, enable: bool):
        configs = self.__helper.lan_configs["if_config"]
        if enable:
            configs["enable_ipv6_pass"] = 1
        else:
            configs["enable_ipv6_pass"] = 0

        return 0, None

    def lan_ipv6_security_enable(self, enable: bool):
        configs = self.__helper.lan_configs["if_config"]
        if enable:
            configs["enable_ipv6_security"] = 1
        else:
            configs["enable_ipv6_security"] = 0

        return 0, None

    def dhcp_positive_heartbeat_set(self, positive_heartbeat=False):
        dhcp = self.__helper.wan_configs["dhcp"]
        if positive_heartbeat:
            dhcp["positive_heartbeat"] = 1
        else:
            dhcp["positive_heartbeat"] = 0

        return 0, None

    def router_config_get(self):
        configs = self.__helper.router_configs

        return 0, configs

    def qos_set_udp_udplite_first(self, enable: bool):
        configs = self.__helper.router_configs["qos"]
        if enable:
            configs["udp_udplite_first"] = 1
        else:
            configs["udp_udplite_first"] = 0
        self.__helper.router.qos_udp_udplite_first_enable(enable)

        return 0, None

    def save(self):
        self.__helper.save_wan_configs()
        self.__helper.save_lan_configs()
        self.__helper.save_router_configs()
        return 0, None

    def port_map_add(self, protocol: int, port: int, address: str, alias_name: str):
        """端口映射添加
        :param protocol:
        :param port:
        :param address:
        :param alias_name:映射名
        :return:
        """
        if protocol not in (6, 17, 136,):
            return RPC.ERR_ARGS, "wrong protocol number value %s" % protocol
        if not netutils.is_port_number(port):
            return RPC.ERR_ARGS, "wrong port number value %s" % port

        if not netutils.is_ipv4_address(address):
            return RPC.ERR_ARGS, "wrong address value %s" % address

        return 0, self.__helper.port_map_add(protocol, port, address, alias_name)

    def port_map_del(self, protocol: int, port: int):
        if protocol not in (6, 17, 136,):
            return RPC.ERR_ARGS, "wrong protocol number value %s" % protocol
        if not netutils.is_port_number(port):
            return RPC.ERR_ARGS, "wrong port number value %s" % port

        return 0, self.__helper.port_map_del(protocol, port)

    def port_map_configs_get(self):
        return 0, self.__helper.port_map_configs

    def src_filter_set_ip(self, ip: str, prefix: int, is_ipv6=False):
        if is_ipv6:
            byte_addr = socket.inet_pton(socket.AF_INET6, ip)
        else:
            byte_addr = socket.inet_pton(socket.AF_INET, ip)

        return 0, self.__helper.router.src_filter_set_ip(byte_addr, prefix, is_ipv6);

    def src_filter_enable(self, enable: bool):
        return 0, self.__helper.router.src_filter_enable(enable)

    def src_filter_set_protocols(self, protocol: str):
        seq = list(bytes(0xff))
        if protocol == "UDP" or protocol == "ALL":
            seq[17] = 1
        if protocol == "TCP" or protocol == "ALL":
            seq[6] = 1
        if protocol == "UDPLite" or protocol == "ALL":
            seq[136] = 1

        byte_data = bytes(seq)

        return 0, self.__helper.router.src_filter_set_protocols(byte_data)


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

    __pppoe = None
    __pppoe_enable = None
    __pppoe_user = None
    __pppoe_passwd = None

    __conf_dir = None
    __rpc_instance = None

    __gc_gen = None

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
            # os.system("echo 1 > /proc/sys/net/ipv4/ip_forward")

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
        """
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
        self.__gc_gen = 0

        self.__wan_configs = {}
        self.__is_linux = sys.platform.startswith("linux")
        self.__rpc_instance = rpc(self)

        if not debug: self.__router.clog_set("/tmp/ixcsys/router/stdout.log", "/tmp/ixcsys/router/stderr.log")

        # FreeBSDif_tap.ko
        if not self.is_linux:
            fd = os.popen("kldstat")
            s = fd.read()
            fd.close()
            p = s.find("if_tap.ko")
            if p < 0: os.system("kldload if_tap")

        gc.disable()

    def start(self):
        self.start_lan()
        self.start_wan()

        self.set_router()

        self.load_port_map_configs()
        self.reset_port_map()

    @property
    def router(self):
        return self.__router

    def pppoe_session_handle(self, protocol: int, byte_data: bytes):
        """
        """
        self.__pppoe.handle_packet_from_ns(protocol, byte_data)

    @property
    def pppoe_user(self):
        return self.__pppoe_user

    @property
    def pppoe_passwd(self):
        return self.__pppoe_passwd

    def rpc_fn_call(self, name: str, arg_data: bytes):
        """
        :return (is_error,byte_message)
        """
        dic = pickle.loads(arg_data)
        if not isinstance(dic, dict):
            return RPC.ERR_SYS, "wrong RPC request procotol"

        if "args" not in dic:
            return RPC.ERR_SYS, "wrong RPC request procotol"

        if "kwargs" not in dic:
            return RPC.ERR_SYS, "wrong RPC request procotol"

        args = dic["args"]
        kwargs = dic["kwargs"]

        if not isinstance(args, tuple) or (not isinstance(kwargs, dict)):
            return RPC.ERR_SYS, "wrong RPC request procotol"

        return self.__rpc_instance.call(name, *args, **kwargs)

    def tell(self, cmd: str, *args):
        """
        """
        if cmd == "lcp_start":
            if self.__pppoe: self.__pppoe.start_lcp()
        if cmd == "lcp_stop":
            if self.__pppoe: self.__pppoe.stop_lcp()

    def loop(self):
        """
        """
        self.__pppoe.loop()

        gc.enable()
        gc.collect(generation=self.__gc_gen)
        self.__gc_gen += 1
        if self.__gc_gen > 2: self.__gc_gen = 0
        gc.disable()
