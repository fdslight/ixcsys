#!/usr/bin/env python3

import zlib
import ixc_syscore.sysadm.web.controllers.controller as base_controller

import ixc_syslib.pylib.RPCClient as RPC


class controller(base_controller.BaseController):
    def myinit(self):
        self.request.set_allow_methods(["POST"])
        return True

    def parse_rules(self, s: str):
        _list = s.split("\n")
        results = []

        for s in _list:
            s = s.replace("\r", "")
            s = s.replace("\t", "")
            s = s.replace(" ", "")
            s = s.strip()
            if not s: continue
            if s[0] == "#": continue
            results.append(s)

        return results

    def handle(self):
        action = self.request.get_argument("action", is_seq=False, is_qs=False)
        rule = self.request.get_argument("rule", is_seq=False, is_qs=False)

        if action not in ("rule_adds", "rule_del", "rule_dels", "rules_modify",):
            self.json_resp(True, "错误的动作请求参数")
            return

        if not rule and action != "rules_modify":
            self.json_resp(True, "空的规则")
            return

        if rule is None: rule = ""

        rule = rule.strip()

        if action == "rule_adds":
            RPC.fn_call("DNS", "/rule", "sec_rules_add", self.parse_rules(rule))
            RPC.fn_call("DNS", "/config", "save")
            self.json_resp(False, {})
        elif action == "rule_dels":
            RPC.fn_call("DNS", "/rule", "sec_rules_del", self.parse_rules(rule))
            RPC.fn_call("DNS", "/config", "save")
            self.json_resp(False, {})
        elif action == "rules_modify":
            rule_file_fpath = "/tmp/ixcsys/sec-dns-rule.txt"
            fdst = open(rule_file_fpath, "w", errors='ignore')
            fdst.write(rule)
            fdst.close()
            try:
                RPC.fn_call("DNS", "/rule", "sec_rules_modify_with_fpath", rule_file_fpath)
            except RPC.RPCErr:
                self.json_resp(True, "系统错误")
                return
            RPC.fn_call("DNS", "/config", "save")
            self.json_resp(False, {})
        else:
            RPC.fn_call("DNS", "/rule", "sec_rule_del", rule)
            RPC.fn_call("DNS", "/config", "save")
            self.json_resp(False, {})
