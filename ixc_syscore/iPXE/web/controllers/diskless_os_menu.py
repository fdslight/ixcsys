#!/usr/bin/env python3
# 无盘操作系统菜单

import ixc_syscore.sysadm.web.controllers.controller as base_controller


class controller(base_controller.BaseController):
    def myinit(self):
        self.request.set_allow_methods(["GET"])
        return True

    def handle(self):
        self.finish_with_text(b"")
