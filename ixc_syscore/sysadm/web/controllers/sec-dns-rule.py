#!/usr/bin/env python3

import ixc_syscore.sysadm.web.controllers.controller as base_controller

import ixc_syslib.pylib.RPCClient as RPC


class controller(base_controller.BaseController):
    def myinit(self):
        self.request.set_allow_methods(["POST"])
        return True

    def handle(self):
        action = self.request.get_argument("action", is_seq=False, is_qs=False)
        rule = self.request.get_argument("rule", is_seq=False, is_qs=False)

        if action not in ("rule_add", "rule_del",):
            self.json_resp(True, "错误的动作请求参数")
            return

        if not rule:
            self.json_resp(True, "空的规则")
            return

        rule = rule.strip()

        if action == "rule_add":
            RPC.fn_call("DNS", "/rule", "sec_rule_add", rule)
            RPC.fn_call("DNS", "/config", "save")
            self.json_resp(False, {})
        else:
            RPC.fn_call("DNS", "/rule", "sec_rule_del", rule)
            RPC.fn_call("DNS", "/config", "save")
            self.json_resp(False, {})