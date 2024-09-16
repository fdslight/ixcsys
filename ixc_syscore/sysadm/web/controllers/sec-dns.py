#!/usr/bin/env python3

import pywind.lib.netutils as netutils

import ixc_syscore.sysadm.web.controllers.controller as base_controller
import ixc_syslib.pylib.RPCClient as RPC


class controller(base_controller.BaseController):
    def myinit(self):
        self.request.set_allow_methods(["POST"])
        return True

    def handle_add(self):
        qtype = self.request.get_argument("qtype", is_seq=False, is_qs=False)
        host = self.request.get_argument("host", is_seq=False, is_qs=False)
        addr = self.request.get_argument("addr", is_seq=False, is_qs=False)

        if qtype not in ("A", "AAAA",):
            self.json_resp(True, "提交了错误的DNS查询类型值")
            return

        if not host:
            self.json_resp(True, "空的域名值")
            return

        if not addr:
            self.json_resp(True, "空的地址值")
            return

        if qtype == "AAAA" and not netutils.is_ipv6_address(addr):
            self.json_resp(True, "提交的地址不是有效的IPv6地址")
            return

        if qtype == "A" and not netutils.is_ipv4_address(addr):
            self.json_resp(True, "提交的地址不是有效的IPv4地址")
            return

        if qtype == "AAAA":
            is_ipv6 = True
        else:
            is_ipv6 = False

        is_ok = RPC.fn_call("DNS", "/config", "hosts_set", host, addr, is_ipv6=is_ipv6)

        if not is_ok:
            self.json_resp(True, "设置%s记录失败" % qtype)
            return

        RPC.fn_call("DNS", "/config", "hosts_save")

        self.json_resp(False, "设置%s记录成功" % qtype)


    def handle_delete(self):
        qtype = self.request.get_argument("qtype", is_seq=False, is_qs=False)
        host = self.request.get_argument("host", is_seq=False, is_qs=False)

        if qtype not in ("A", "AAAA",):
            self.json_resp(True, "提交了错误的DNS查询类型值")
            return

        if not host:
            self.json_resp(True, "空的域名值")
            return

        if qtype == "AAAA":
            is_ipv6 = True
        else:
            is_ipv6 = False

        RPC.fn_call("DNS", "/config", "hosts_set", host, "", is_ipv6=is_ipv6)
        RPC.fn_call("DNS", "/config", "hosts_save")

        self.json_resp(False, "删除%s记录成功" % qtype)

    def handle(self):
        action = self.request.get_argument("action", is_seq=False, is_qs=False)
        if not action:
            self.handle_add()
        else:
            self.handle_delete()
