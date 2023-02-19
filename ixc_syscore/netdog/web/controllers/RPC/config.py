#!/usr/bin/env python3

import ixc_syslib.web.controllers.rpc_controller as rpc

import ixc_syslib.pylib.RPCClient as RPC

from pywind.global_vars import global_vars
import pywind.lib.netutils as netutils


class controller(rpc.controller):
    __runtime = None

    def rpc_init(self):
        self.__runtime = global_vars["ixcsys.netdog"]

        self.fobjs = {
            "config_get": self.config_get,
        }

    def config_get(self):
        return 0, None
