#!/usr/bin/env python3
import pywind.lib.netutils as netutils
import ixc_syscore.DHCP.pylib.dhcp as dhcp


class dhcp_client(object):
    __my_ipaddr = None

    __hostname = None
    __hwaddr = None

    __dhcp_parser = None
    __dhcp_builder = None

    __runtime = None

    def __init__(self, runtime, hostname: str, hwaddr: str):
        self.__runtime = runtime
        self.__hostname = hostname
        self.__hwaddr = netutils.ifaddr_to_bytes(hwaddr)

        self.__dhcp_parser = dhcp.dhcp_parser()
        self.__dhcp_builder = dhcp.dhcp_builder()

    def handle_dhcp_response(self, response_data: bytes):
        pass

    def do(self):
        """自动执行
        """
        pass

    def send_dhcp_request(self):
        link_data = self.__dhcp_builder.build_to_link_data(
            bytes([0xff, 0xff, 0xff, 0xff, 0xff, 0xff]),
            self.__hwaddr,
            bytes([0xff, 0xff, 0xff, 0xff]),
            bytes(4),
            [],
            is_server=False
        )
        self.__runtime.send_dhcp_client_msg(link_data)

    def dhcp_ok(self):
        pass
