#!/usr/bin/env python3

import socket

import ixc_syslib.web.controllers.rpc_controller as rpc

from pywind.global_vars import global_vars

import ixc_syslib.pylib.RPCClient as RPC

import pywind.lib.netutils as netutils


class controller(rpc.controller):
    __runtime = None

    def rpc_init(self):
        self.__runtime = global_vars["ixcsys.runtime"]

        self.fobjs = {
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
            "save": self.save
        }

    def wan_config_get(self):
        return 0, self.__runtime.wan_configs

    def lan_config_get(self):
        return 0, self.__runtime.lan_configs

    def manage_addr_get(self):
        lan_configs = self.__runtime.lan_configs

        return 0, lan_configs["if_config"]["manage_addr"]

    def wan_hwaddr_set(self, hwaddr: str):
        if not netutils.is_hwaddr(hwaddr):
            return RPC.ERR_ARGS, "wrong hwaddr format"

        configs = self.__runtime.wan_configs
        configs["public"]["hwaddr"] = hwaddr

        return 0, None

    def cur_internet_type_get(self):
        """获取当前internet上网方式
        """
        wan_configs = self.__runtime.wan_configs
        public = wan_configs["public"]

        return 0, public["internet_type"]

    def pppoe_set(self, username: str, passwd: str, heartbeat=False):
        if not username or not passwd:
            return RPC.ERR_ARGS, "empty username or password"
        configs = self.__runtime.wan_configs
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

        public = self.__runtime.wan_configs["public"]
        public["internet_type"] = _type

        return 0, None

    def wan_addr_set(self, ip: str, mask: str, gw: str):
        if not netutils.is_ipv4_address(ip) or not netutils.is_mask(mask) or not netutils.is_ipv4_address(gw):
            return RPC.ERR_ARGS, "wrong argument value format"

        prefix = netutils.mask_to_prefix(mask, is_ipv6=False)
        if not netutils.is_same_network(ip, gw, prefix, is_ipv6=False):
            return RPC.ERR_ARGS, "wrong argument value"

        ipv4 = self.__runtime.wan_configs["ipv4"]
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

        configs = self.__runtime.lan_configs["if_config"]
        configs["ip6_addr"] = "%s/%s" % (subnet, prefix,)

        return 0, None

    def lan_static_ipv6_enable(self, enable: bool):
        """是否开启静态IPv6地址
        """
        configs = self.__runtime.lan_configs["if_config"]
        if enable:
            configs["enable_static_ipv6"] = 1
        else:
            configs["enable_static_ipv6"] = 0

        return 0, None

    def lan_ipv6_pass_enable(self, enable: bool):
        configs = self.__runtime.lan_configs["if_config"]
        if enable:
            configs["enable_ipv6_pass"] = 1
        else:
            configs["enable_ipv6_pass"] = 0

        return 0, None

    def lan_ipv6_security_enable(self, enable: bool):
        configs = self.__runtime.lan_configs["if_config"]
        if enable:
            configs["enable_ipv6_security"] = 1
        else:
            configs["enable_ipv6_security"] = 0

        return 0, None

    def dhcp_positive_heartbeat_set(self, positive_heartbeat=False):
        dhcp = self.__runtime.wan_configs["dhcp"]
        if positive_heartbeat:
            dhcp["positive_heartbeat"] = 1
        else:
            dhcp["positive_heartbeat"] = 0

        return 0, None

    def router_config_get(self):
        configs = self.__runtime.router_configs

        return 0, configs

    def qos_set_udp_udplite_first(self, enable: bool):
        configs = self.__runtime.router_configs["qos"]
        if enable:
            configs["udp_udplite_first"] = 1
        else:
            configs["udp_udplite_first"] = 0
        self.__runtime.router.qos_udp_udplite_first_enable(enable)

        return 0, None

    def save(self):
        self.__runtime.save_wan_configs()
        self.__runtime.save_lan_configs()
        self.__runtime.save_router_configs()
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

        return 0, self.__runtime.port_map_add(protocol, port, address, alias_name)

    def port_map_del(self, protocol: int, port: int):
        if protocol not in (6, 17, 136,):
            return RPC.ERR_ARGS, "wrong protocol number value %s" % protocol
        if not netutils.is_port_number(port):
            return RPC.ERR_ARGS, "wrong port number value %s" % port

        return 0, self.__runtime.port_map_del(protocol, port)

    def port_map_configs_get(self):
        return 0, self.__runtime.port_map_configs

    def src_filter_set_ip(self, ip: str, prefix: int, is_ipv6=False):
        if is_ipv6:
            byte_addr = socket.inet_pton(socket.AF_INET6, ip)
        else:
            byte_addr = socket.inet_pton(socket.AF_INET, ip)

        return 0, self.__runtime.router.src_filter_set_ip(byte_addr, prefix, is_ipv6);

    def src_filter_enable(self, enable: bool):
        return 0, self.__runtime.router.src_filter_enable(enable)

    def src_filter_set_protocols(self, protocol: str):
        seq = list(bytes(0xff))
        if protocol == "UDP" or protocol == "ALL":
            seq[17] = 1
        if protocol == "TCP" or protocol == "ALL":
            seq[6] = 1
        if protocol == "UDPLite" or protocol == "ALL":
            seq[136] = 1

        byte_data = bytes(seq)

        return 0, self.__runtime.router.src_filter_set_protocols(byte_data)
