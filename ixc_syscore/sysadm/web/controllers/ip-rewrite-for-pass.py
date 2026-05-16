#!/usr/bin/env python3
import json

import ixc_syscore.sysadm.web.controllers.controller as base_controller
import pywind.lib.netutils as netutils
import ixc_syslib.pylib.RPCClient as RPC


class controller(base_controller.BaseController):
    def myinit(self):
        self.request.set_allow_methods(["POST"])
        return True

    def handle(self):
        enable = self.request.get_argument("enable", is_seq=False, is_qs=False)
        dest_ip = self.request.get_argument("dest_ip", is_seq=False, is_qs=False)
        old_src_ip = self.request.get_argument("old_src_ip", is_seq=False, is_qs=False)
        new_src_ip = self.request.get_argument("new_src_ip", is_seq=False, is_qs=False)

        if not enable:
            enable = False
        else:
            enable = True

        if not dest_ip:
            dest_ip = "0.0.0.0"
        if not old_src_ip:
            old_src_ip = "0.0.0.0"
        if not new_src_ip:
            new_src_ip = "0.0.0.0"

        if not netutils.is_ipv4_address(dest_ip):
            self.json_resp(True, "错误的目标IP地址格式")
            return
        if not netutils.is_ipv4_address(old_src_ip):
            self.json_resp(True, "错误的原始IP地址格式")
            return
        if not netutils.is_ipv4_address(new_src_ip):
            self.json_resp(True, "错误的新的IP地址格式")
            return

        RPC.fn_call("router", "/config", "ip_rewrite_for_pass_set", dest_ip, old_src_ip, new_src_ip)
        RPC.fn_call("router", "/config", "ip_rewrite_for_pass_enable", enable)
        RPC.fn_call("router", "/config", "config_save")

        self.json_resp(False, {})
