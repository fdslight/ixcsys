#!/usr/bin/env python3
import socket

import pywind.lib.netutils as netutils


def ipaddr_plus_plus(byte_addr: bytes):
    """对IP地址进行++操作
    """
    _list = list(byte_addr)
    _list.reverse()
    _list_new = []

    overflow = 0
    is_first = True
    for i in _list:
        if not is_first and overflow < 1:
            _list_new.append(i)
            continue
        if is_first:
            x = i + 1
            if x > 0xff:
                x = 0
                overflow = 1
            is_first = False
        else:
            x = i + overflow
            if x > 0xff:
                x = 0
            else:
                overflow = 0

        _list_new.append(x)

    _list_new.reverse()

    return bytes(_list_new)


class alloc(object):
    __empty_ipaddrs = None

    # IP 地址与MAC地址的绑定
    __bind = None

    __begin_addr = None
    __end_addr = None

    # 当前地址
    __cur_byte_addr = None

    # 不可用的地址映射记录
    __unable_addr_map = None

    __prefix = None
    __is_ipv6 = None
    __subnet = None

    def __init__(self, addr_begin: str, addr_end: str, subnet: str, prefix: int, is_ipv6=False):
        self.__bind = {}
        self.__empty_ipaddrs = []

        if is_ipv6:
            fa = socket.AF_INET6
        else:
            fa = socket.AF_INET

        self.__begin_addr = socket.inet_pton(fa, addr_begin)
        self.__end_addr = socket.inet_pton(fa, addr_end)
        self.__cur_byte_addr = self.__begin_addr
        self.__unable_addr_map = {}
        self.__prefix = prefix
        self.__is_ipv6 = is_ipv6
        self.__subnet = subnet

    def bind_ipaddr(self, hwaddr: str, ipaddr: str):
        self.__bind[hwaddr] = ipaddr

    def unbind_ipaddr(self, hwaddr: str):
        if hwaddr in self.__bind:
            del self.__bind[hwaddr]

    def get_ipaddr(self):
        if self.__empty_ipaddrs:
            byte_addr = self.__empty_ipaddrs.pop(0)
            return byte_addr

        rs_addr = self.__cur_byte_addr
        byte_addr = ipaddr_plus_plus(self.__cur_byte_addr)

        if self.__is_ipv6:
            addr = socket.inet_ntop(socket.AF_INET6, byte_addr)
        else:
            addr = socket.inet_ntop(socket.AF_INET, byte_addr)

        rs = netutils.is_subnet(addr, self.__prefix, self.__subnet)

        if not rs: return None
        self.__cur_byte_addr = byte_addr

        return rs_addr
