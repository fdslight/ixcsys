#!/usr/bin/env python3

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
            "lan_static_ipv6_enable": self.lan_static_ipv6_enable,
            "lan_static_ipv6_pass_enable": self.lan_static_ipv6_pass_enable,
            "lan_static_ipv6_set": self.lan_static_ipv6_set,
            "pppoe_set": self.pppoe_set,
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

        if not netutils.is_subnet(subnet, prefix, subnet, is_ipv6=True):
            return RPC.ERR_ARGS, "wrong subnet value"

        configs = self.__runtime.lan_configs["if_config"]
        configs["ip6_addr"] = "%s/%s" % (subnet, prefix,)

        return 0, None

    def lan_static_ipv6_pass_enable(self, enable: bool):
        """是否开启或者关闭静态IPv6直通
        """
        configs = self.__runtime.lan_configs["if_config"]
        if enable:
            configs["enable_static_ipv6_passthrough"] = 1
        else:
            configs["enable_static_ipv6_passthrough"] = 0

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

    def dhcp_positive_heartbeat_set(self, positive_heartbeat=False):
        dhcp = self.__runtime.wan_configs["dhcp"]
        if positive_heartbeat:
            dhcp["positive_heartbeat"] = 1
        else:
            dhcp["positive_heartbeat"] = 0

        return 0, None

    def save(self):
        self.__runtime.save_wan_configs()
        self.__runtime.save_lan_configs()
        return 0, None
