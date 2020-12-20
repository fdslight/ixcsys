#!/usr/bin/env python3

import ixc_syslib.web.controllers.rpc_controller as rpc

from pywind.global_vars import global_vars

import ixc_syslib.pylib.RPCClient as RPC


class controller(rpc.controller):
    __runtime = None

    def rpc_init(self):
        self.__runtime = global_vars["ixcsys.proxy_helper"]

        self.fobjs = {
        }

    def route_add(self, subnet: str, prefix: int, is_ipv6=False, timeout=0):
        pass

    def route_del(self, subnet: str, prefix: int, is_ipv6=False):
        pass

    def proxy_helper_enable(self, enable: bool):
        """是否开启代理助手
        """
        pass
