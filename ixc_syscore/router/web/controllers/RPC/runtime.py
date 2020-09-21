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
            "get_all_pkt_flags": self.get_all_pkt_flags
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
