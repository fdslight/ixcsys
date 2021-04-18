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
        manage_addr = self.request.get_argument("manage_addr", is_seq=False, is_qs=False)
        mask = self.request.get_argument("mask", is_seq=False, is_qs=False)
        ip_addr = self.request.get_argument("ip_addr", is_seq=False, is_qs=False)

        if not hwaddr:
            self.json_resp(True, "wrong hardware address format")
            return
        if not netutils.is_hwaddr(hwaddr):
            self.json_resp(True, "wrong hardware address format")
            return
        if not manage_addr:
            self.json_resp(True, "空的管理地址")
            return
        if not mask:
            self.json_resp(True, "空的子网掩码")
            return

        if not netutils.is_ipv4_address(manage_addr):
            self.json_resp(True, "错误的管理地址格式")
            return

        if not netutils.is_mask(mask):
            self.json_resp(True, "错误的掩码格式")
            return

        if not ip_addr:
            self.json_resp(True, "空的路由器地址")
            return

        if not netutils.is_ipv4_address(ip_addr):
            self.json_resp(True, "错误的路由器地址格式")
            return

        prefix = netutils.mask_to_prefix(mask, is_ipv6=False)
        subnet_a = netutils.calc_subnet(ip_addr, prefix, is_ipv6=False)
        subnet_b = netutils.calc_subnet(manage_addr, prefix, is_ipv6=False)

        if subnet_a != subnet_b:
            self.json_resp(True, "管理地址和路由器地址不在同一个局域网内")
            return

        RPC.fn_call("router", "/config", "lan_hwaddr_set", hwaddr)
        RPC.fn_call("router", "/config", "manage_addr_set", manage_addr)
        RPC.fn_call("router", "/config", "lan_addr_set", ip_addr, mask)

        RPC.fn_call("router", "/config", "config_save")

        self.json_resp(False, "")

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
