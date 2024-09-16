#!/usr/bin/env python3
from cgitb import enable

import ixc_syscore.sysadm.web.controllers.controller as base_controller
import ixc_syslib.pylib.RPCClient as RPC

import pywind.lib.netutils as netutils


class controller(base_controller.BaseController):
    def myinit(self):
        self.request.set_allow_methods(["POST"])
        return True

    def handle(self):
        enable_edns = self.request.get_argument("enable_edns", is_qs=False, is_seq=False, default="")
        ip4_auto = self.request.get_argument("ipv4.enable_auto", is_qs=False, is_seq=False)
        ip6_auto = self.request.get_argument("ipv6.enable_auto", is_qs=False, is_seq=False)
        enable_dnsv6_drop = self.request.get_argument("enable_dnsv6_drop", is_qs=False, is_seq=False)
        enable_dns_no_system_drop = self.request.get_argument("enable_dns_no_system_drop", is_qs=False, is_seq=False)

        try:
            enable_edns = int(enable_edns)
        except ValueError:
            enable_edns = 0

        enable_edns = bool(enable_edns)

        if not ip4_auto:
            ip4_auto = False
        else:
            ip4_auto = True
        if not ip6_auto:
            ip6_auto = False
        else:
            ip6_auto = True

        if not enable_dnsv6_drop:
            enable_dnsv6_drop = False
        else:
            enable_dnsv6_drop = True

        if not enable_dns_no_system_drop:
            enable_dns_no_system_drop = False
        else:
            enable_dns_no_system_drop = True

        ipv4_main_dns = self.request.get_argument("ipv4.main_dns", is_qs=False, is_seq=False)
        ipv4_second_dns = self.request.get_argument("ipv4.second_dns", is_qs=False, is_seq=False)

        ipv6_main_dns = self.request.get_argument("ipv6.main_dns", is_qs=False, is_seq=False)
        ipv6_second_dns = self.request.get_argument("ipv6.second_dns", is_qs=False, is_seq=False)

        if not ip4_auto:
            if not ipv4_main_dns:
                self.json_resp(True, self.LA("please set main IPv4 DNS address"))
                return
            ''''''
        if not ip6_auto:
            if not ipv6_main_dns:
                self.json_resp(True, self.LA("please set main IPv6 DNS address"))
                return

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

        RPC.fn_call("DNS", "/config", "enable", ip4_auto, is_ipv6=False)
        RPC.fn_call("DNS", "/config", "enable", ip6_auto, is_ipv6=True)
        RPC.fn_call("DNS", "/config", "set_dnsv6_drop_enable", enable_dnsv6_drop)
        RPC.fn_call("DNS", "/config", "dns_no_system_drop_enable", enable_dns_no_system_drop)
        RPC.fn_call("DNS", "/config", "save")

        RPC.fn_call("secDNS", "/config", "enable", enable_edns)

        self.json_resp(False, {})
