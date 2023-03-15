#!/usr/bin/env python3

import struct
import ixc_syslib.pylib.ev_handlers.nspkt as nspkt
import ixc_syslib.pylib.logging as logging

FMT="!6sBB16sQQQ"

class traffic_log_handler(nspkt.nspkt_handler):
    def handle_recv(self, if_type: int, ipproto: int, flags: int, message: bytes):
        print(message)
