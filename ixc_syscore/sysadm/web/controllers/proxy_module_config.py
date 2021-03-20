#!/usr/bin/env python3

import ixc_syscore.sysadm.web.controllers.controller as base_controller

import ixc_syslib.pylib.RPCClient as RPC


class controller(base_controller.BaseController):
    def myinit(self):
        self.request.set_allow_methods(["GET", "POST"])
        return True

    def handle_post(self):
        self.finish_with_json({})

    def handle_get(self):
        name = self.request.get_argument("module", is_seq=False, is_qs=True)
        conf = RPC.fn_call("proxy", "/config", "get_crypto_module_conf", name)
        if conf == None:
            is_error = True
            msg = "没有找到加密模块%s" % name
        else:
            is_error = False
            msg = conf
        self.finish_with_json({"is_error": is_error, "message": msg})

    def handle(self):
        if self.request.environ["REQUEST_METHOD"].upper() == "GET":
            self.handle_get()
            return
        self.handle_post()
