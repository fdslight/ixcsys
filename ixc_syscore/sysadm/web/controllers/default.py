#!/usr/bin/env python3

import ixc_syscore.sysadm.web.controllers.controller as base_controller


class controller(base_controller.BaseController):
    def handle(self):
        self.render("base.html")
