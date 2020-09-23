#!/usr/bin/env python3

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
            "get_all_pkt_flags": self.get_all_pkt_flags,
            "get_wan_hwaddr": self.get_wan_hwaddr,
            "get_lan_hwaddr": self.get_lan_hwaddr,
            "get_lan_ipaddr": self.get_lan_ipaddr,
            "get_wan_ipaddr": self.get_wan_ipaddr,
            "get_lan_manage_ipaddr": self.get_lan_manage_ipaddr
        }

    def get_all_pkt_flags(self):
        """获取所有转发数据包的flags
        :return:
        """
        values = {
            "IXC_FLAG_DHCP_CLIENT": router.IXC_FLAG_DHCP_CLIENT,
            "IXC_FLAG_DHCP_SERVER": router.IXC_FLAG_DHCP_SERVER
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

    def get_lan_hwaddr(self):
        """获取LAN硬件地址
        :return:
        """
        if_config = self.__runtime.lan_configs["if_config"]
        r = (0, (if_config["phy_ifname"], if_config["hwaddr"],),)

        return r

    def get_lan_ipaddr(self, is_ipv6=False):
        pass

    def get_wan_ipaddr(self, is_ipv6=False):
        pass

    def get_lan_manage_ipaddr(self, is_ipv6=False):
        pass
