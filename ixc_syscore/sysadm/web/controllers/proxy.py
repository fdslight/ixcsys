#!/usr/bin/env python3

import ixc_syscore.sysadm.web.controllers.controller as base_controller

import ixc_syslib.pylib.RPCClient as RPC


class controller(base_controller.BaseController):
    def myinit(self):
        self.request.set_allow_methods(["POST"])
        return True

    def handle_post(self):
        self.finish_with_json({})

    def handle_rules(self, _type: str):
        text = self.request.get_argument("text", is_seq=False, is_qs=False)

        if not text:
            self.json_resp(True, "未提交任何表单数据")
            return

        fn = ""
        if _type == "dns":
            fn = "dns_rule_update"
        elif _type == "proxy-ip":
            fn = "proxy_ip_rule_update"
        else:
            fn = "pass_ip_rule_update"

        print(fn)
        RPC.fn_call("proxy", "/config", fn, text)

        self.json_resp(False, {})

    def handle(self):
        _type = self.request.get_argument("type", is_seq=False, is_qs=True)
        _types = (
            "conn", "dns", "proxy-ip", "pass-ip",
        )

        if _type not in _types:
            self.json_resp(True, "错误的请求类型")
            return

        if _type != "conn":
            self.handle_rules(_type)
            return
        self.json_resp(False, {})
