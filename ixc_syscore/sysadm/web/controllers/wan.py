#!/usr/bin/env python3

import sys, platform, os, psutil
import ixc_syscore.sysadm.web.controllers.controller as base_controller


class controller(base_controller.BaseController):
    def myinit(self):
        self.request.set_allow_methods(["GET", "POST"])
        return True

    def handle_get(self):
        self.finish_with_json({"is_error": False, "message": {}})

    def handle_post(self):
        self.finish_with_json({})

    def handle(self):
        method = self.request.environ["REQUEST_METHOD"]
        if method == "GET":
            self.handle_get()
        else:
            self.handle_post()
