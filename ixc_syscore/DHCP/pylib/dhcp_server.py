#!/usr/bin/env python3

import ixc_syscore.DHCP.pylib.dhcp as dhcp
import ixc_syscore.DHCP.pylib.netpkt as netpkt

class dhcp_server(object):
    __my_ipaddr = None

    __hostname = None
    __hwaddr = None

    __dhcp_parser = None
    __dhcp_builder = None

    __runtime = None

    # MAC与IP地址的绑定
    __bind = None

    __dst_hwaddr = None

    def __init__(self, runtime, hostname: str, hwaddr: str, addr_begin: str, addr_finish: str):
        self.__bind = {}
        self.__runtime = runtime
        self.__dhcp_parser = dhcp.dhcp_parser()
        self.__dhcp_builder = dhcp.dhcp_builder()

    def bind_ipaddr(self, hwaddr: str, ip_addr: str):
        """对特定的MAC地址进行IP地址绑定
        """
        self.__bind[hwaddr] = ip_addr

    @property
    def bind(self):
        return self.__bind

    def handle_dhcp_msg(self, msg: bytes):
        result = self.__dhcp_parser.parse_from_link_data(msg)

    def handle_arp(self, dst_hwaddr: bytes, src_hwaddr: bytes, arp_info):
        # 只允许广播和发送到本机器的ARP数据包
        brd = bytes([0xff, 0xff, 0xff, 0xff, 0xff, 0xff])
        if dst_hwaddr != brd or dst_hwaddr != self.__hwaddr: return

        op, _dst_hwaddr, _src_hwaddr, src_ipaddr, dst_ipaddr = arp_info
        if _dst_hwaddr != self.__hwaddr: return

    def loop(self):
        pass
