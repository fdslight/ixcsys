#!/usr/bin/env python3

import ixc_syslib.pylib.ev_handlers.nspkt as nspkt


class traffic_log_handler(nspkt.nspkt_handler):
    def handle_recv(self, if_type: int, ipproto: int, flags: int, message: bytes):
        print(message)
