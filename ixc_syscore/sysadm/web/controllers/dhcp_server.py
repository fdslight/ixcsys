#!/usr/bin/env python3

import ixc_syscore.sysadm.web.controllers.controller as base_controller
import ixc_syslib.pylib.RPCClient as RPC


class controller(base_controller.BaseController):
    def myinit(self):
        self.request.set_allow_methods(["POST"])
        return True

    def handle(self):
        s_enable_dhcp = self.request.get_argument("enable_dhcp", is_seq=False, is_qs=False)
        addr_begin = self.request.get_argument("addr_begin", is_seq=False, is_qs=False)
        addr_end = self.request.get_argument("addr_end", is_seq=False, is_qs=False)
        boot_file = self.request.get_argument("boot_file", is_seq=False, is_qs=False)

        if not s_enable_dhcp:
            enable_dhcp = False
        else:
            enable_dhcp = True

        RPC.fn_call("DHCP", "/dhcp_server", "enable", enable_dhcp)
        RPC.fn_call("DHCP", "/dhcp_server", "boot_file_set", boot_file)
        RPC.fn_call("DHCP", "/dhcp_server", "alloc_addr_range_set", addr_begin, addr_end)
        RPC.fn_call("DHCP", "/dhcp_server", "save")

        self.json_resp(False, {})
