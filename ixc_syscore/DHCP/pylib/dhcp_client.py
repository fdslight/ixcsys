#!/usr/bin/env python3
import struct, random, time
import pywind.lib.netutils as netutils
import ixc_syscore.DHCP.pylib.dhcp as dhcp


class dhcp_client(object):
    __my_ipaddr = None

    __hostname = None
    __hwaddr = None

    __dhcp_parser = None
    __dhcp_builder = None

    __runtime = None

    __dhcp_step = None

    __xid = None

    __up_time = None

    __dhcp_ok = None

    __rebind_time = None
    __renewal_time = None

    def __init__(self, runtime, hostname: str, hwaddr: str):
        self.__runtime = runtime
        self.__hostname = hostname
        self.__hwaddr = netutils.ifaddr_to_bytes(hwaddr)
        self.__dhcp_step = 0

        self.__dhcp_parser = dhcp.dhcp_parser()
        self.__dhcp_builder = dhcp.dhcp_builder()
        self.__up_time = time.time()
        self.__dhcp_ok = False

    def handle_dhcp_response(self, response_data: bytes):
        try:
            dst_hwaddr, src_hwaddr, dst_addr, src_addr, options, is_server = self.__dhcp_parser.parse_from_link_data(
                response_data)
        except:
            return

        print(options)

    def send_dhcp_discover(self):
        self.__dhcp_parser.xid = random.randint(1, 0xfffffffe)
        self.__xid = self.__dhcp_parser.xid

        options = [
            # dhcp msg type
            (53, struct.pack("b", 1)),
            # client id
            (61, self.__hwaddr,),
            # vendor
            (43, "ixcsys".encode(),),
            # parameter request list
            (55, struct.pack("BBBBBB", 0, 1, 3, 6, 28, 50))
        ]

        link_data = self.__dhcp_builder.build_to_link_data(
            bytes([0xff, 0xff, 0xff, 0xff, 0xff, 0xff]),
            self.__hwaddr,
            bytes([0xff, 0xff, 0xff, 0xff]),
            bytes(4),
            options,
            is_server=False
        )
        self.__runtime.send_dhcp_client_msg(link_data)

    def get_dhcp_opt_value(self, options: list, code: int):
        rs = None
        for name, length, value in options:
            if name == code:
                rs = value
                break
            ''''''
        return rs

    def send_dhcp_request(self):
        """发送DHCP请求报文
        :return:
        """
        pass

    def send_dhcp_release(self):
        """发送DHCP release报文
        :return:
        """
        pass

    def send_dhcp_decline(self):
        """发送DHCP decline报文
        :return:
        """
        pass

    def do(self):
        """自动执行
        """
        if self.dhcp_ok:
            self.dhcp_keep_handle()
            return

        if 0 == self.__dhcp_step:
            self.__dhcp_step = 1
            self.send_dhcp_discover()

    @property
    def dhcp_ok(self):
        return self.__dhcp_ok

    def handle(self, msg: bytes):
        print(msg)
        self.handle_dhcp_response(msg)

    def dhcp_keep_handle(self):
        """保持DHCP地址
        :return:
        """
        pass
