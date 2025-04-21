#!/usr/bin/env python3
# 实现dhcpv6客户端stateless

import time


class dhcpv6c(object):
    __duid = None
    __xid = None

    __hosname = None
    __wan_hwaddr = None

    __up_time = None

    def __init__(self, hostname, wan_hwaddr):
        self.__hostname = hostname
        self.__wan_hwaddr = wan_hwaddr
        self.__up_time = time.time()

    def send_link_data(self, dst_hwaddr: str, src_hwaddr: str, link_data: int, byte_data: bytes):
        """发送链路层数据"""
        pass

    def send_ip_data(self, dst_ip6: str, src_ip6: str, data: bytes):
        pass

    def send_udp_data(self, dst_ip6: str, src_ip6: str, data: bytes):
        return

    def send_dhcp_request(self):
        pass

    def handle_dhcp_msg(self, ether_data: bytes):
        pass

    def loop(self):
        now = time.time()
        if now - self.__up_time < 30:
            return
        self.__up_time = now
