#!/usr/bin/env python3

import ixc_syslib.pylib.ev_handlers.nspkt as nspkt

import ixc_syscore.proxy.pylib.base_proto.utils as proto_utils


class netpkt_handler(nspkt.nspkt_handler):
    def handle_recv(self, if_type: int, ipproto: int, flags: int, message: bytes):
        if ipproto not in (1, 6, 17, 44, 58,): return
        self.dispatcher.send_msg_to_tunnel(proto_utils.ACT_IPDATA, message)
