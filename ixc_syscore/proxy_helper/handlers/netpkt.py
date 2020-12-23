#!/usr/bin/env python3

import ixc_syslib.pylib.ev_handlers.nspkt as nspkt


class nspkt_handler(nspkt.nspkt_handler):
    @property
    def consts(self):
        return self.dispatcher.consts

    @property
    def proxy_helper(self):
        return self.dispatcher.proxy_helper

    def handle_recv(self, if_type: int, ipproto: int, flags: int, message: bytes):
        if ipproto not in (6, 17, 136,): return

        self.proxy_helper.netpkt_handle(message)

    def send_ip_msg(self, message: bytes):
        """发送IP消息
        """
        self.send_msg(self.consts["IXC_NETIF_LAN"], self.consts["IXC_FLAG_ROUTE_FWD"], message)
