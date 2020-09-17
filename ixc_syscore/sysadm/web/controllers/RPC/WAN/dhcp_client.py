#!/usr/bin/env python3

import ixc_syslib.web.controllers.rpc_controller as rpc


class controller(rpc.controller):
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
