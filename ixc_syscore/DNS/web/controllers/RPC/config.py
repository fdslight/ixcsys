#!/usr/bin/env python3

import ixc_syslib.web.controllers.rpc_controller as rpc

from pywind.global_vars import global_vars


class controller(rpc.controller):
    __runtime = None

    def rpc_init(self):
        self.__runtime = global_vars["ixcsys.DNS"]

        self.fobjs = {
        }

    def set_parent_server(self, server_ip, is_ipv6=False):
        """设置上游服务器IP地址
        """
        pass
