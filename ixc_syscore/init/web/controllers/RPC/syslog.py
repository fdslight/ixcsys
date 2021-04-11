#!/usr/bin/env python3

from pywind.global_vars import global_vars

import ixc_syslib.web.controllers.rpc_controller as rpc


class controller(rpc.controller):
    __runtime = None

    def rpc_init(self):
        self.__runtime = global_vars["ixcsys.init"]

        self.fobjs = {
            "syslog_get": self.syslog_get,
            "errlog_get": self.errlog_get,
        }

    def syslog_get(self):
        return 0, self.__runtime.get_syslog()

    def errlog_get(self):
        return 0, self.__runtime.get_errlog()
