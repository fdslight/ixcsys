#!/usr/bin/env python3

import ixc_syslib.web.controllers.rpc_controller as rpc
from pywind.global_vars import global_vars


class controller(rpc.controller):
    @property
    def dhcp(self):
        return global_vars["ixcsys.DHCP"]

    def rpc_init(self):
        self.fobjs = {
            "after_enable": self.aftr_enable,
        }

    def aftr_enable(self, enable):
        self.dhcp.client6.enable_aftr(enable)

        return 0, None
