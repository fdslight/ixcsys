#!/usr/bin/env python3

import ixc_syscore.sysadm.web.controllers.controller as base_controller

import ixc_syslib.pylib.RPCClient as RPC


class controller(base_controller.BaseController):
    def myinit(self):
        self.request.set_allow_methods(["POST"])
        return True

    def handle_post(self):
        self.finish_with_json({})

    def handle(self):
        file_dir = self.request.get_argument("file_dir", is_seq=False, is_qs=False)
        enable_v6 = self.request.get_argument("enable_ipv6", is_seq=False, is_qs=False)

        js = {"enable_ipv6": enable_v6, "file_dir": file_dir}

        RPC.fn_call("tftp", "/config", "config_write", js)

        self.json_resp(False, js)
