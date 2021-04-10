#!/usr/bin/env python3

import ixc_syscore.sysadm.web.controllers.controller as base_controller

import ixc_syslib.pylib.RPCClient as RPC

import pywind.lib.netutils as netutils


class controller(base_controller.BaseController):
    def myinit(self):
        self.request.set_allow_methods(["POST"])
        return True

    def handle_wan_submit(self):
        hwaddr = self.request.get_argument("hwaddr", is_seq=False, is_qs=False)
        if not hwaddr:
            self.json_resp(True, "wrong hardware address format")
            return
        if not netutils.is_hwaddr(hwaddr):
            self.json_resp(True, "wrong hardware address format")
            return

        RPC.fn_call("router", "/config", "wan_hwaddr_set", hwaddr)
        RPC.fn_call("router", "/config", "config_save")
        self.json_resp(False, "")

    def handle_lan_submit(self):
        hwaddr = self.request.get_argument("hwaddr", is_seq=False, is_qs=False)
        if not hwaddr:
            self.json_resp(True, "wrong hardware address format")
            return
        if not netutils.is_hwaddr(hwaddr):
            self.json_resp(True, "wrong hardware address format")
            return

    def handle(self):
        _type = self.request.get_argument("type", is_qs=True, is_seq=False)
        types = [
            "lan", "wan",
        ]
        if _type not in types:
            self.json_resp(True, "unknown request type")
            return

        if _type == "lan":
            self.handle_lan_submit()
        else:
            self.handle_wan_submit()
