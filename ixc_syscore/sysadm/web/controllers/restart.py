#!/usr/bin/env python3

from pywind.global_vars import global_vars
import ixc_syscore.sysadm.web.controllers.controller as base_controller


class controller(base_controller.BaseController):
    def myinit(self):
        self.request.set_allow_methods(["GET"])
        return True

    def handle(self):
        system = global_vars["ixcsys.sysadm"]
        system.restart()

        self.finish_with_json({"is_error": False, "message": "正在重启中,请至少等待1分钟"})
