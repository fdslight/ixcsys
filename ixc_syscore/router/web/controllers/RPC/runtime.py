#!/usr/bin/env python3
import socket

import pywind.lib.netutils as netutils

import ixc_syslib.web.controllers.rpc_controller as rpc
import ixc_syscore.router.pylib.router as router

from pywind.global_vars import global_vars


class controller(rpc.controller):
    __runtime = None

    @property
    def router(self):
        return global_vars["ixcsys.router"]

    def rpc_init(self):
        self.__runtime = global_vars["ixcsys.runtime"]

        self.fobjs = {
            "get_all_consts": self.get_all_consts,
            "get_wan_ipaddr_info": self.get_wan_ipaddr_info,
            "add_route": self.add_route,
            "del_route": self.del_route
        }

    def get_all_consts(self):
        """获取所有转发数据包的flags
        :return:
        """
        values = {
            "IXC_FLAG_DHCP_CLIENT": router.IXC_FLAG_DHCP_CLIENT,
            "IXC_FLAG_DHCP_SERVER": router.IXC_FLAG_DHCP_SERVER,
            "IXC_FLAG_ARP": router.IXC_FLAG_ARP,
            "IXC_FLAG_L2VPN": router.IXC_FLAG_L2VPN,
            "IXC_FLAG_SRC_FILTER": router.IXC_FLAG_SRC_FILTER,
            "IXC_FLAG_ROUTE_FWD": router.IXC_FLAG_ROUTE_FWD,
            "IXC_NETIF_LAN": router.IXC_NETIF_LAN,
            "IXC_NETIF_WAN": router.IXC_NETIF_WAN,
        }

        return (0, values,)

    def get_wan_hwaddr(self):
        """获取WAN硬件地址
        :return:
        """
        wan_configs = self.__runtime.wan_configs
        public = wan_configs["public"]

        r = (0, (public["phy_ifname"], public["hwaddr"],),)

        return r

    def get_gw_hwaddr(self):
        """获取LAN硬件地址
        :return:
        """
        if_config = self.__runtime.lan_configs["if_config"]
        r = (0, (if_config["phy_ifname"], if_config["hwaddr"],),)

        return r

    def get_wan_ipaddr_info(self, is_ipv6=False):
        pass

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
        set_ok = self.router.netif_set_ip(router.IXC_NETIF_LAN, byte_ip, prefix, is_ipv6)

        return 0, (set_ok, "")

    def set_manage_ipaddr(self, ipaddr: str, is_ipv6=False, is_local=False):
        """设置管理地址
        """
        self.__runtime.set_manage_ipaddr(ipaddr, is_ipv6=is_ipv6, is_local=is_local)
        return 0, None

    def get_manage_ipaddr(self):
        """获取管理地址
        """
        ipaddr = self.__runtime.get_manage_addr()

        return 0, ipaddr

    def get_lan_configs(self):
        return 0, self.__runtime.lan_configs

    def get_wan_configs(self):
        return 0, self.__runtime.wan_configs

    def set_wan_ipaddr(self, ipaddr: str, prefix: int, is_ipv6=False):
        """设置WAN口的IP地址
        """
        check_ok, err_msg = self.check_ipaddr_args(ipaddr, int(prefix), is_ipv6=is_ipv6)
        if not check_ok:
            return 0, (check_ok, err_msg,)

        if self.router.pppoe_is_enabled():
            return 0, (False, "PPPoE is enabled,cannot set wan IP or IPv6 address")

        if is_ipv6:
            fa = socket.AF_INET6
        else:
            fa = socket.AF_INET
        byte_ip = socket.inet_pton(fa, ipaddr)
        set_ok = self.router.netif_set_ip(router.IXC_NETIF_WAN, byte_ip, prefix, is_ipv6)

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

        rs = self.router.route_add(byte_subnet, prefix, byte_gw, is_ipv6)

        return 0, (rs, "")

    def del_route(self, subnet: str, prefix: int, is_ipv6=False):
        ok, mesg = self.check_ipaddr_args(subnet, prefix, is_ipv6=is_ipv6)

        if not ok: return 0, (ok, mesg)

        if is_ipv6:
            fa = socket.AF_INET6
        else:
            fa = socket.AF_INET

        byte_subnet = socket.inet_pton(fa, subnet)
        self.router.route_del(byte_subnet, prefix, is_ipv6)

        return 0, (True, "")

    def pppoe_is_enabled(self):
        is_enabled = self.router.pppoe_is_enabled()

        return 0, is_enabled
