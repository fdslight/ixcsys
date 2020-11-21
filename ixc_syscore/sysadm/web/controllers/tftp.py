#!/usr/bin/env python3

import ixc_syscore.sysadm.web.controllers.controller as base_controller

import ixc_syslib.pylib.RPCClient as RPC


class controller(base_controller.BaseController):
    def myinit(self):
        self.request.set_allow_methods(["GET", "POST"])
        return True

    def handle_get(self):
        if not RPC.RPCReadyOk("tftp"):
            self.json_resp(True, "cannot found tftp process")
            return
        result = RPC.fn_call("tftp", "/config", "config_get")
        self.json_resp(False, result)

    def handle_post(self):
        self.finish_with_json({})

    def handle(self):
        method = self.request.environ["REQUEST_METHOD"]
        if method == "GET":
            self.handle_get()
        else:
            self.handle_post()
