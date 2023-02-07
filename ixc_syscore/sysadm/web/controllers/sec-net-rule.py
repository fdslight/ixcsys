#!/usr/bin/env python3

import pywind.lib.netutils as netutils

import ixc_syscore.sysadm.web.controllers.controller as base_controller

import ixc_syslib.pylib.RPCClient as RPC


class controller(base_controller.BaseController):
    def myinit(self):
        self.request.set_allow_methods(["POST"])
        return True

    def handle_add_src(self, hwaddr: str):
        rule_act = self.request.get_argument("rule_act", is_seq=False, is_qs=False)
        if rule_act not in ("accept", "drop",):
            self.json_resp(True, "错误的规则行为值")
            return

        RPC.fn_call("router", "/config", "sec_net_add_src", hwaddr, rule_act)
        RPC.fn_call("router", "/config", "config_save")

        self.json_resp(False, {})

    def handle_add_dst(self, hwaddr: str):
        network = self.request.get_argument("network", is_seq=False, is_qs=False)

        rs = netutils.parse_ip_with_prefix(network)
        if not rs:
            self.json_resp(True, "错误的网络地址格式")
            return

        subnet, prefix = rs
        if prefix < 0:
            self.json_resp(True, "错误的网络前缀值")
            return

        if not netutils.is_ipv4_address(subnet) and not netutils.is_ipv6_address(subnet):
            self.json_resp(True, "错误的网络地址格式")
            return

        if netutils.is_ipv6_address(subnet):
            is_ipv6 = True
        else:
            is_ipv6 = False

        subnet = netutils.calc_subnet(subnet, prefix, is_ipv6=is_ipv6)

        RPC.fn_call("router", "/config", "sec_net_add_dst", hwaddr, subnet, prefix, is_ipv6=is_ipv6)
        RPC.fn_call("router", "/config", "config_save")

        self.json_resp(False, {})

    def handle_del(self, hwaddr: str):
        RPC.fn_call("router", "/config", "sec_net_del_src", hwaddr)
        RPC.fn_call("router", "/config", "config_save")

        self.json_resp(False, {})

    def handle(self):
        hwaddr = self.request.get_argument("hwaddr", is_seq=False, is_qs=False)
        action = self.request.get_argument("action", is_seq=False, is_qs=False)

        if action not in ("dst_add", "src_add", "src_del",):
            self.json_resp(True, "未知的请求动作")
            return

        if not hwaddr:
            self.json_resp(True, "空的硬件地址")
            return

        if not netutils.is_hwaddr(hwaddr):
            self.json_resp(True, "错误的硬件地址格式")
            return

        if action == "dst_add":
            self.handle_add_dst(hwaddr)
            return

        if action == "src_add":
            self.handle_add_src(hwaddr)
            return

        self.handle_del(hwaddr)
