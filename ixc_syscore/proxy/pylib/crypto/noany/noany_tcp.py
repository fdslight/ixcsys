#!/usr/bin/env python3

import ixc_syscore.proxy.pylib.base_proto.tunnel_tcp as tunnel


class encrypt(tunnel.builder):
    def __init__(self):
        super().__init__(tunnel.MIN_FIXED_HEADER_SIZE)


class decrypt(tunnel.parser):
    def __init__(self):
        super().__init__(tunnel.MIN_FIXED_HEADER_SIZE)
