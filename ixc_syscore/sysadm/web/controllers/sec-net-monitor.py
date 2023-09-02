#!/usr/bin/env python3

import ixc_syscore.sysadm.web.controllers.controller as base_controller
import ixc_syslib.pylib.RPCClient as RPC

import pywind.lib.netutils as netutils


class controller(base_controller.BaseController):
    def myinit(self):
        self.request.set_allow_methods(["POST"])
        return True

    def handle(self):
        hwaddr = self.request.get_argument("hwaddr", is_seq=False, is_qs=False)
        enable = self.request.get_argument("enable", is_seq=False, is_qs=False)

        if not hwaddr:
            self.json_resp(True, "MAC地址不能为空")
            return

        hwaddr = hwaddr.replace("-", ":")
        hwaddr = hwaddr.strip()

        if not netutils.is_hwaddr(hwaddr):
            self.json_resp(True, "错误的MAC地址")
            return

        if not enable:
            enable = False
        else:
            enable = True

        RPC.fn_call("router", "/config", "net_monitor_set", hwaddr, enable=enable)
        RPC.fn_call("router", "/config", "config_save")

        self.json_resp(False, {})
