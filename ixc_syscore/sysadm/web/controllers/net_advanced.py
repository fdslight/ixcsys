#!/usr/bin/env python3

import ixc_syscore.sysadm.web.controllers.controller as base_controller
import ixc_syslib.pylib.RPCClient as RPC

class controller(base_controller.BaseController):
    def myinit(self):
        self.request.set_allow_methods(["POST"])
        return True

    def handle(self):
        udp_udplite_first = self.request.get_argument("udp_udplite_first", is_seq=False, is_qs=False)

        if not udp_udplite_first:
            enable_qos_udp_udplite_first = False
        else:
            enable_qos_udp_udplite_first = True

        RPC.fn_call("router", "/config", "qos_set_udp_udplite_first", enable_qos_udp_udplite_first)
        RPC.fn_call("router", "/config", "config_save")

        self.json_resp(False, {})