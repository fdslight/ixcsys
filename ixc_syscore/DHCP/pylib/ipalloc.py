#!/usr/bin/env python3
import socket


class alloc(object):
    __empty_ipaddrs = None

    # IP 地址与MAC地址的绑定
    __bind = None

    __begin_addr = None
    __end_addr = None

    # 当前地址
    __cur_byte_addr = None

    def __init__(self, addr_begin: str, addr_end: str, is_ipv6=False):
        self.__bind = {}
        self.__empty_ipaddrs = []

        if is_ipv6:
            fa = socket.AF_INET6
        else:
            fa = socket.AF_INET

        self.__begin_addr = socket.inet_pton(fa, addr_begin)
        self.__end_addr = socket.inet_pton(fa, addr_end)

    def bind_ipaddr(self, hwaddr: str, ipaddr: str):
        pass

    def unbind_ipaddr(self, hwaddr: str, ipaddr: str):
        pass

    def get_ipaddr(self):
        pass
