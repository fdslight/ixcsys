#!/usr/bin/env python3

import sys, platform, os, psutil
import ixc_syscore.sysadm.web.controllers.controller as base_controller


class controller(base_controller.BaseController):
    def myinit(self):
        self.request.set_allow_methods(["POST"])
        return True

    def handle(self):
        self.finish_with_text("")
