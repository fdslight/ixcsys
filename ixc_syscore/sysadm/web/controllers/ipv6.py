#!/usr/bin/env python3

import ixc_syscore.sysadm.web.controllers.controller as base_controller

import ixc_syslib.pylib.RPCClient as RPC

import pywind.lib.netutils as netutils


class controller(base_controller.BaseController):
    def myinit(self):
        self.request.set_allow_methods(["POST"])
        return True

    def handle(self):
        ipv6_type = self.request.get_argument("ipv6_type", is_seq=False, is_qs=False)
        ip6_addr = self.request.get_argument("static_ipv6", is_qs=False, is_seq=False)
        ipv6_security = self.request.get_argument("enable_ipv6_security", is_qs=False, is_seq=False)

        if not ipv6_security: ipv6_security = 0
        try:
            enable_ipv6_security = bool(int(ipv6_security))
        except ValueError:
            self.json_resp(True, "wrong enable_ipv6_security value")
            return

        try:
            i_ipv6_type = int(ipv6_type)
        except ValueError:
            self.json_resp(True, "wrong ipv6_type value for data type")
            return

        if i_ipv6_type not in (0, 1, 2,):
            self.json_resp(True, "wrong ipv6_type value")
            return

        enable_static_v6 = False
        enable_ipv6_pass = False

        if i_ipv6_type == 1:
            enable_static_v6 = True
        if i_ipv6_type == 2:
            enable_ipv6_pass = True

        p = ip6_addr.find("/")
        if p < 1:
            self.json_resp(True, "wrong IPv6 address format")
            return

        subnet = ip6_addr[0:p]
        p += 1
        try:
            prefix = int(ip6_addr[p:])
        except ValueError:
            self.json_resp(True, "wrong IPv6 prefix value type")
            return

        if not netutils.is_ipv6_address(subnet):
            self.json_resp(True, "wrong IPv6 address format")
            return

        if prefix < 48 or prefix > 64:
            self.json_resp(True, "IPv6 prefix value must be 48 to 64")
            return

        RPC.fn_call("router", "/config", "lan_ipv6_pass_enable", enable_ipv6_pass)
        RPC.fn_call("router", "/config", "lan_static_ipv6_enable", enable_static_v6)
        RPC.fn_call("router", "/config", "lan_static_ipv6_set", subnet, prefix)
        RPC.fn_call("router", "/config", "lan_ipv6_security_enable", enable_ipv6_security)
        RPC.fn_call("router", "/config", "config_save")

        self.json_resp(False, {})
