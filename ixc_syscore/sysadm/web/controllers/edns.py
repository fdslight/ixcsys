#!/usr/bin/env python3

import pywind.lib.netutils as netutils

import ixc_syscore.sysadm.web.controllers.controller as base_controller
import ixc_syslib.pylib.RPCClient as RPC


class controller(base_controller.BaseController):
    def myinit(self):
        self.request.set_allow_methods(["POST"])
        return True

    def handle_add(self):
        host = self.request.get_argument("host", is_seq=False, is_qs=False)
        port = self.request.get_argument("port", is_seq=False, is_qs=False, default="853")
        hostname = self.request.get_argument("hostname", is_seq=False, is_qs=False, default="")
        comment = self.request.get_argument("comment", is_seq=False, is_qs=False, default="")

        if not netutils.is_ipv4_address(host) and not netutils.is_ipv6_address(host):
            self.json_resp(True, "提交了错误的IP地址,IP地址必须为IPv4或者IPv6")
            return

        try:
            port = int(port)
        except ValueError:
            port = 853

        if port < 1 or port > 65534:
            self.json_resp(True, "错误的DoT服务器端口号值")
            return

        if not hostname:
            self.json_resp(True, "TLS认证主机不能为空")
            return

        RPC.fn_call("secDNS", "/config", "dot_host_add", host, hostname, comment, port=port)
        self.json_resp(False, "添加成功")

    def handle_delete(self):
        host = self.request.get_argument("host", is_seq=False, is_qs=False)

        if host is None:
            self.json_resp(True, "非法表单提交")
            return

        if not netutils.is_ipv4_address(host) and not netutils.is_ipv6_address(host):
            self.json_resp(True, "提交了错误的IP地址,IP地址必须为IPv4或者IPv6")
            return

        RPC.fn_call("secDNS", "/config", "dot_host_del", host)

        self.json_resp(False, "删除DoT记录成功(%s)" % host)

    def handle(self):
        action = self.request.get_argument("action", is_seq=False, is_qs=False)

        if action == "delete":
            self.handle_delete()
        else:
            self.handle_add()
