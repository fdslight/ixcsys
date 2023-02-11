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

        if not enable_auto:
            if not ipv4_main_dns and not ipv6_main_dns:
                self.json_resp(True, self.LA("please set main DNS address"))
                return
            ''''''
        if ipv4_main_dns and not netutils.is_ipv4_address(ipv4_main_dns):
            self.json_resp(True, self.LA("wrong ipv4.main_dns address format"))
            return
        if ipv4_second_dns and not netutils.is_ipv4_address(ipv4_second_dns):
            self.json_resp(True, self.LA("wrong ipv4.second_dns address format"))
            return

        if ipv6_main_dns and not netutils.is_ipv6_address(ipv6_main_dns):
            self.json_resp(True, self.LA("wrong ipv6.main_dns address format"))
            return
        if ipv6_second_dns and not netutils.is_ipv6_address(ipv6_second_dns):
            self.json_resp(True, self.LA("wrong ipv6.second_dns address format"))
            return

        if ipv4_main_dns == ipv4_second_dns and ipv4_main_dns:
            self.json_resp(True, self.LA("there is same for main_dns and second_dns"))
            return
        if ipv6_main_dns == ipv6_second_dns and ipv6_main_dns:
            self.json_resp(True, self.LA("there is same for main_dns and second_dns"))
            return

        if ipv4_main_dns:
            RPC.fn_call("DNS", "/config", "set_parent_server", ipv4_main_dns, is_main_server=True, is_ipv6=False)
        if ipv4_second_dns:
            RPC.fn_call("DNS", "/config", "set_parent_server", ipv4_second_dns, is_main_server=False, is_ipv6=False)
        if ipv6_main_dns:
            RPC.fn_call("DNS", "/config", "set_parent_server", ipv6_main_dns, is_main_server=True, is_ipv6=True)
        if ipv6_second_dns:
            RPC.fn_call("DNS", "/config", "set_parent_server", ipv6_second_dns, is_main_server=False, is_ipv6=True)

        RPC.fn_call("DNS", "/config", "enable", enable_auto)
        RPC.fn_call("DNS", "/config", "save")

        self.json_resp(False, {})
