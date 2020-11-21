#!/usr/bin/env python3

import ixc_syslib.web.controllers.rpc_controller as rpc

from pywind.global_vars import global_vars


class controller(rpc.controller):
    __runtime = None

    def rpc_init(self):
        self.__runtime = global_vars["ixcsys.tftp"]

        self.fobjs = {
            "config_get": self.config_get,
        }

    def config_get(self):
        return 0, self.__runtime.configs["conf"]
