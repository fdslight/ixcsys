#!/usr/bin/env python3

from pywind.global_vars import global_vars

import ixc_syslib.web.controllers.rpc_controller as rpc


class controller(rpc.controller):
    __runtime = None

    def rpc_init(self):
        self.__runtime = global_vars["ixcsys.init"]

        self.fobjs = {
        }
