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

    def handle(self, msg: bytes):
        try:
            dst_hwaddr, src_hwaddr, proto_type, ippkt = netpkt.parse_ether_data(msg)
        except:
            return
        self.__dst_hwaddr = src_hwaddr
        try:
            src_addr, dst_addr, protocol, udpdata = netpkt.parse_ippkt(ippkt)
            src_port, dst_port, dhcpdata = netpkt.parse_udppkt(udpdata)
        except:
            return

        try:
            self.__dhcp_parser.parse_public_header(dhcpdata[0:dhcp.HDR_LENGTH])
            options = self.__dhcp_parser.parse_options(dhcpdata[dhcp.HDR_LENGTH:])
        except:
            return

