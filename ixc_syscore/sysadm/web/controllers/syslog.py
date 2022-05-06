#!/usr/bin/env python3

from pywind.global_vars import global_vars
import ixc_syscore.sysadm.web.controllers.controller as base_controller


class controller(base_controller.BaseController):
    def myinit(self):
        self.request.set_allow_methods(["POST"])
        return True

    def handle(self):
        fdst = open("/var/log/ixcsys_error.log", "w")
        fdst.close()

        self.json_resp(False, {})
