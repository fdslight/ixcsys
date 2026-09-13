#!/usr/bin/env python3

import ixc_syscore.sysadm.web.controllers.controller as base_controller


class controller(base_controller.BaseController):
    def myinit(self):
        self.request.set_allow_methods(["POST"])
        return True

    def handle(self):
        script_content = self.request.get_argument("script-content", is_seq=False, is_qs=False)

        self.json_resp(True,"错误的请求内容")

        #self.json_resp(False, {})
