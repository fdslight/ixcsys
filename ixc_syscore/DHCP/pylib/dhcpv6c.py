#!/usr/bin/env python3

class dhcpv6c(object):
    __pppoe_enable = None
    __duid = None
    __iaid = None
    # IPv6地址前缀
    __address_prefix = None

    def __init__(self):
        self.__pppoe_enable = False

    def loop(self):
        # pppoe未开启那么就不处理
        if not self.__pppoe_enable: return
