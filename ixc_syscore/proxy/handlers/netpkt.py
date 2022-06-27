#!/usr/bin/env python3

import ixc_syslib.pylib.ev_handlers.nspkt as nspkt


class netpkt_handler(nspkt.nspkt_handler):
    __is_g_ip6_tunnel = None

    def my_init(self, is_g_ip6_tunnel=False):
        """是否是全局IP6转发隧道
        """
        self.__is_g_ip6_tunnel = is_g_ip6_tunnel

    def handle_recv(self, if_type: int, ipproto: int, flags: int, message: bytes):
        if ipproto not in (1, 6, 17, 44, 58,): return
        self.dispatcher.handle_msg_from_local(message, is_g_ip6_tunnel=self.__is_g_ip6_tunnel)
