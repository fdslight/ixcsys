#!/usr/bin/env python3

import ixc_syslib.pylib.ev_handlers.nspkt as nspkt


class nspkt_handler(nspkt.nspkt_handler):
    def handle_recv(self, if_type: int, ipproto: int, flags: int, message: bytes):
        pass

    def send_ip_msg(self, message: bytes):
        """发送IP消息
        """
        pass