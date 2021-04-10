#!/usr/bin/env python3

import ixc_syscore.sysadm.web.controllers.controller as base_controller
import ixc_syslib.pylib.RPCClient as RPC

import pywind.lib.netutils as netutils


class controller(base_controller.BaseController):
    def myinit(self):
        self.request.set_allow_methods(["POST"])
        return True

    def handle_pppoe(self):
        username = self.request.get_argument("username", is_seq=False, is_qs=False)
        passwd = self.request.get_argument("passwd", is_seq=False, is_qs=False)
        s_heartbeat_enable = self.request.get_argument("heartbeat", is_qs=False, is_seq=False)

        if not s_heartbeat_enable:
            heartbeat_enable = False
        else:
            heartbeat_enable = True

        if not username or not passwd:
            self.json_resp(True, "username or passwd cannot empty")
            return

        RPC.fn_call("router", "/config", "pppoe_set", username, passwd, heartbeat=heartbeat_enable)
        RPC.fn_call("router", "/config", "internet_type_set", "pppoe")
        RPC.fn_call("router", "/config", "save")

        self.json_resp(False, {})

    def handle_static_ip(self):
        ip = self.request.get_argument("ip", is_qs=False, is_seq=False)
        mask = self.request.get_argument("mask", is_qs=False, is_seq=False)
        gw = self.request.get_argument("gateway", is_qs=False, is_seq=False)

        if not ip:
            self.json_resp(True, self.LA("empty IP address"))
            return

        if not mask:
            self.json_resp(True, self.LA("empty mask value"))
            return

        if not netutils.is_mask(mask):
            self.json_resp(True, self.LA("wrong mask format"))
            return

        if not gw:
            self.json_resp(True, self.LA("empty gateway address"))
            return

        if not netutils.is_ipv4_address(ip):
            self.json_resp(True, self.LA("wrong IP address format"))
            return

        if not netutils.is_ipv4_address(mask):
            self.json_resp(True, self.LA("wrong mask format"))
            return

        if not netutils.is_ipv4_address(gw):
            self.json_resp(True, self.LA("wrong gateway address format"))
            return

        prefix = netutils.mask_to_prefix(mask, is_ipv6=False)
        if not netutils.is_same_network(ip, gw, prefix, is_ipv6=False):
            self.json_resp(True, self.LA("there is different network for ip address and gateway"))
            return

        RPC.fn_call("router", "/config", "wan_addr_set", ip, mask, gw)
        RPC.fn_call("router", "/config", "internet_type_set", "static-ip")
        RPC.fn_call("router", "/config", "save")

        self.json_resp(False, {})

    def handle_dhcp(self):
        s = self.request.get_argument("positive_heartbeat", is_qs=False, is_seq=False)

        if not s:
            b = False
        else:
            b = True

        RPC.fn_call("router", "/config", "internet_type_set", "dhcp")
        RPC.fn_call("router", "/config", "dhcp_positive_heartbeat_set", positive_heartbeat=b)
        RPC.fn_call("router", "/config", "config_save")

        self.json_resp(False, {})

    def handle(self):
        _type = self.request.get_argument("type", is_qs=True, is_seq=False)
        if _type not in ("pppoe", "dhcp", "static-ip",):
            self.json_resp(True, "wrong request internet type")
            return

        if _type == "pppoe":
            self.handle_pppoe()
            return
        if _type == "dhcp":
            self.handle_dhcp()
            return
        if _type == "static-ip":
            self.handle_static_ip()
            return
