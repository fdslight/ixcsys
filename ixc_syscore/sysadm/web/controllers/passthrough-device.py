#!/usr/bin/env python3

import pywind.lib.netutils as netutils

import ixc_syscore.sysadm.web.controllers.controller as base_controller
import ixc_syslib.pylib.RPCClient as RPC


class controller(base_controller.BaseController):
    def myinit(self):
        self.request.set_allow_methods(["POST"])
        return True

    def handle_add(self):
        hwaddr = self.request.get_argument("hwaddr", is_seq=False, is_qs=False)
        comment = self.request.get_argument("comment", is_seq=False, is_qs=False, default="")

        if hwaddr is None:
            self.json_resp(True, "设备MAC地址不能为空")
            return

        hwaddr = hwaddr.replace("-", ":")

        if not netutils.is_hwaddr(hwaddr):
            self.json_resp(True, "错误的设备MAC地址格式")
            return

        RPC.fn_call("router", "/config", "passthrough_device_add", hwaddr, comment=comment)
        self.json_resp(False, "添加成功")

    def handle_delete(self):
        hwaddr = self.request.get_argument("hwaddr", is_seq=False, is_qs=False)

        if hwaddr is None:
            self.json_resp(True, "非法表单提交")
            return

        if not netutils.is_hwaddr(hwaddr):
            self.json_resp(True, "错误的设备MAC地址格式")
            return

        RPC.fn_call("router", "/config", "passthrough_device_del", hwaddr)

        self.json_resp(False, "删除记录成功")

    def handle(self):
        action = self.request.get_argument("action", is_seq=False, is_qs=False)

        if action == "delete":
            self.handle_delete()
        else:
            self.handle_add()
