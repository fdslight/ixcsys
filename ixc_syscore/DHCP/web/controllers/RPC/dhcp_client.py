#!/usr/bin/env python3

import ixc_syslib.web.controllers.rpc_controller as rpc
from pywind.global_vars import global_vars


class controller(rpc.controller):
    @property
    def dhcp(self):
        return global_vars["ixcsys.dhcp"]

    def rpc_init(self):
        self.fobjs = {
            "ip_get_ok": self.ip_get_ok,
            "ip_addr_get": self.ip_addr_get,
            "subnet_mask_get": self.subnet_mask_get,
            "broadcast_addr_get": self.broadcast_addr_get,
            "dnsserver_addr_get": self.dnsserver_addr_get,
            "router_addr_get": self.router_addr_get,
            "reset": self.reset
        }

    def ip_get_ok(self):
        r = (0, self.dhcp.client.dhcp_ok,)
        return r

    def ip_addr_get(self):
        if not self.dhcp.client.dhcp_ok: return (0, None,)
        r = (0, self.dhcp.client.ip_addr_get(),)
        return r

    def subnet_mask_get(self):
        if not self.dhcp.client.dhcp_ok: return (0, None,)
        r = (0, self.dhcp.client.subnet_mask_get(),)
        return r

    def broadcast_addr_get(self):
        if not self.dhcp.client.dhcp_ok: return (0, None,)
        r = (0, self.dhcp.client.broadcast_addr_get(),)
        return r

    def dnsserver_addr_get(self):
        if not self.dhcp.client.dhcp_ok: return (0, None,)
        r = (0, self.dhcp.client.dnsserver_addr_get(),)
        return r

    def router_addr_get(self):
        if not self.dhcp.client.dhcp_ok: return (0, None,)
        r = (0, self.dhcp.client.router_addr_get(),)
        return r

    def reset(self):
        self.dhcp.client.reset()
        return 0, None
