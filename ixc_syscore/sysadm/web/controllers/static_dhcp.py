#!/usr/bin/env python3

import pywind.lib.netutils as netutils
import ixc_syscore.sysadm.web.controllers.controller as base_controller
import ixc_syslib.pylib.RPCClient as RPC


class controller(base_controller.BaseController):
    def myinit(self):
        self.request.set_allow_methods(["POST"])
        return True

    def handle_add(self):
        name = self.request.get_argument("alias-name", is_seq=False, is_qs=False)
        hwaddr = self.request.get_argument("hwaddr", is_seq=False, is_qs=False)
        ip = self.request.get_argument("ip", is_seq=False, is_qs=False)

        if not name or not hwaddr or not ip:
            self.finish_with_json({"is_error": True, "message": "不能提交空的选项"})
            return

        if not netutils.is_hwaddr(hwaddr):
            self.finish_with_json({"is_error": True, "message": "错误的硬件地址格式"})
            return

        if not netutils.is_ipv4_address(ip):
            self.finish_with_json({"is_error": True, "message": "错误的IP地址格式"})
            return

        RPC.fn_call("DHCP", "/dhcp_server", "add_dhcp_bind", name, hwaddr, ip)
        self.finish_with_json({"is_error": False, "message": "添加成功"})

    def handle_del(self):
        ip = self.request.get_argument("ip", is_seq=False, is_qs=False)
        if not ip:
            self.finish_with_json({"is_error": True, "message": "不能提交空的选项"})
            return

        RPC.fn_call("DHCP", "/dhcp_server", "del_dhcp_bind", ip)
        self.finish_with_json({"is_error": False, "message": "删除成功"})

    def handle(self):
        action = self.request.get_argument("action", is_seq=False, is_qs=False)

        if action not in ("add", "del",):
            self.finish_with_json({"is_error": True, "message": "错误的请求动作"})
            return

        if action == "add":
            self.handle_add()
        else:
            self.handle_del()
