#!/usr/bin/env python3

from pywind.global_vars import global_vars

import ixc_syslib.web.controllers.rpc_controller as rpc


class controller(rpc.controller):
    @property
    def router(self):
        return global_vars["ixcsys.router"]

    def rpc_init(self):
        self.fobjs = {
            "dhcp_client_enable": self.dhcp_client_enable
        }

    def dhcp_client_enable(self, enable: bool):
        """启用或者关闭DHCP客户端
        :param enable:
        :return:
        """
        return (0, enable,)
