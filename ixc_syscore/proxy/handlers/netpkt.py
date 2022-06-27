#!/usr/bin/env python3

import ixc_syslib.pylib.ev_handlers.nspkt as nspkt

class netpkt_handler(nspkt.nspkt_handler):
    def handle_recv(self, if_type: int, ipproto: int, flags: int, message: bytes):
        if ipproto not in (1, 6, 17, 44, 58,): return
        self.dispatcher.handle_msg_from_local(message)
