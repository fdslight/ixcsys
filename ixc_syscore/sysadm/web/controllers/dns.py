#!/usr/bin/env python3

import ixc_syscore.sysadm.web.controllers.controller as base_controller
import ixc_syslib.pylib.RPCClient as RPC

import pywind.lib.netutils as netutils


class controller(base_controller.BaseController):
    def myinit(self):
        self.request.set_allow_methods(["POST"])
        return True

    def handle(self):
        auto = self.request.get_argument("enable_auto", is_qs=False, is_seq=False)

        if not auto:
            enable_auto = False
        else:
            enable_auto = True

        ipv4_main_dns = self.request.get_argument("ipv4.main_dns", is_qs=False, is_seq=False)
        ipv4_second_dns = self.request.get_argument("ipv4.second_dns", is_qs=False, is_seq=False)

        ipv6_main_dns = self.request.get_argument("ipv6.main_dns", is_qs=False, is_seq=False)
        ipv6_second_dns = self.request.get_argument("ipv6.second_dns", is_qs=False, is_seq=False)

        if ipv4_main_dns and not netutils.is_ipv4_address(ipv4_main_dns):
            self.json_resp(True, "wrong ipv4.main_dns address format")
            return
        if ipv4_second_dns and not netutils.is_ipv4_address(ipv4_second_dns):
            self.json_resp(True, "wrong ipv4.second_dns address format")
            return

        if ipv6_main_dns and not netutils.is_ipv6_address(ipv6_main_dns):
            self.json_resp(True, "wrong ipv6.main_dns address format")
            return
        if ipv6_second_dns and not netutils.is_ipv6_address(ipv6_second_dns):
            self.json_resp(True, "wrong ipv6.second_dns address format")
            return

        self.json_resp(False, {})
