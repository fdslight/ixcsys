#!/usr/bin/env python3

import ixc_syscore.sysadm.web.controllers.controller as base_controller

import ixc_syslib.pylib.RPCClient as RPC

import pywind.lib.netutils as netutils


class controller(base_controller.BaseController):
    def myinit(self):
        self.request.set_allow_methods(["POST"])
        return True

    def handle(self):
        enable_static_v6 = self.request.get_argument("enable_static_ipv6", is_seq=False, is_qs=False)
        enable_pass = self.request.get_argument("enable_static_ipv6_pass", is_qs=False, is_seq=False)
        ip6_addr = self.request.get_argument("static_ipv6",is_qs=False,is_seq=False)

        if not enable_static_v6:
            RPC.fn_call("router", "/config", "lan_static_ipv6_enable", False)
            RPC.fn_call("router", "/config", "save")
            self.json_resp(False, {})
            return

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

        if not netutils.is_subnet(subnet, prefix, subnet, is_ipv6=True):
            self.json_resp(True, "wrong IPv6 subnet value")
            return

        if not enable_pass:
            RPC.fn_call("router", "/config", "lan_static_ipv6_pass_enable", False)
        else:
            RPC.fn_call("router", "/config", "lan_static_ipv6_pass_enable", True)

        RPC.fn_call("router", "/config", "lan_static_ipv6_enable", True)
        RPC.fn_call("router", "/config", "lan_static_ipv6_set", subnet, prefix)
        RPC.fn_call("router", "/config", "save")

        self.json_resp(False, {})
