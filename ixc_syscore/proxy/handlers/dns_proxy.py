#!/usr/bin/env python3

import pywind.evtframework.handlers.udp_handler as udp_handler
import ixc_syslib.pylib.ev_handlers.nspkt as nspkt


class dns_proxy(udp_handler.udp_handler):
    def init_func(self, creator_fd):
        pass

    def udp_readable(self, message, address):
        if address[0] != "127.0.0.1": return