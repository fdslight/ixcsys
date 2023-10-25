#!/usr/bin/env python3

import os
import ixc_syscore.sysadm.web.controllers.controller as base_controller

import ixc_syslib.pylib.RPCClient as RPC


class controller(base_controller.BaseController):
    def myinit(self):
        self.request.set_allow_methods(["POST"])
        return True

    def handle(self):
        ip_tcp_mss = self.request.get_argument("ip_tcp_mss", is_seq=False, is_qs=False)
        ip6_tcp_mss = self.request.get_argument("ip6_tcp_mss", is_seq=False, is_qs=False)

        if not ip_tcp_mss: ip_tcp_mss = "0"
        if not ip6_tcp_mss: ip6_tcp_mss = "0"

        try:
            ip_tcp_mss = int(ip_tcp_mss)
        except ValueError:
            self.json_resp(True, "错误的IPv4 TCP MSS值类型 %s" % ip_tcp_mss)
            return

        try:
            ip6_tcp_mss = int(ip6_tcp_mss)
        except ValueError:
            self.json_resp(True, "错误的IPv6 TCP MSS值类型 %s" % ip_tcp_mss)
            return

        if ip_tcp_mss != 0:
            if ip_tcp_mss < 536 or ip_tcp_mss > 1460:
                self.json_resp(True, "错误的MSS数值,IPv4 TCP MSS值范围为536~1460")
                return
            ''''''
        if ip6_tcp_mss != 0:
            if ip6_tcp_mss < 516 or ip6_tcp_mss > 1440:
                self.json_resp(True, "错误的MSS数值,IPv6 TCP MSS值范围为516~1440")
                return
            ''''''

        RPC.fn_call("router", "/config", "tcp_mss_set", ip_tcp_mss, is_ipv6=False)
        RPC.fn_call("router", "/config", "tcp_mss_set", ip6_tcp_mss, is_ipv6=True)

        self.json_resp(False, "修改TCP MSS成功")
