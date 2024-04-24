#!/usr/bin/env python3

import ixc_syslib.web.controllers.rpc_controller as rpc
from pywind.global_vars import global_vars


class controller(rpc.controller):
    @property
    def _pass(self):
        return global_vars["ixcsys.PASS"]

    def rpc_init(self):
        self.fobjs = {
            "get_connected_device": self.get_connected_device,
        }

    def get_connected_device(self):
        return 0, self._pass.device_name
