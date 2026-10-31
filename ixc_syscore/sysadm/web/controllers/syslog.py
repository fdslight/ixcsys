#!/usr/bin/env python3

import ixc_syscore.sysadm.web.controllers.controller as base_controller
import ixc_syslib.pylib.RPCClient as RPC

class controller(base_controller.BaseController):
    def myinit(self):
        self.request.set_allow_methods(["POST"])
        return True

    def handle(self):
        RPC.fn_call("init","/syslog","errlog_clear_immediately")
        self.json_resp(False, {})
