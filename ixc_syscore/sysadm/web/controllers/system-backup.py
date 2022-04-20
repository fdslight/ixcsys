#!/usr/bin/env python3

import ixc_syscore.sysadm.web.controllers.controller as base_controller

from pywind.global_vars import global_vars


class controller(base_controller.BaseController):
    def myinit(self):
        self.request.set_allow_methods(["POST"])
        return True

    @property
    def sysadm(self):
        return global_vars["ixcsys.sysadm"]

    def handle(self):
        self.json_resp(False, "")
