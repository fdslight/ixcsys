#!/usr/bin/env python3

import struct, random
import ixc_syscore.DHCP.pylib.netpkt as netpkt

DHCP_OP_REQ = 1
DHCP_OP_RESP = 2

DHCP_OPS = [
    DHCP_OP_REQ, DHCP_OP_RESP
]


class DHCPErr(Exception): pass


HDR_FMT = "!BBBBIHH4s4s4s4s16s64s128sI"

HDR_LENGTH = 240


class dhcp(object):
    op = None
    hw_type = None
    hw_len = None
    h_ops = None
    xid = None
    secs = None
    flags = None

    ciaddr = None
    yiaddr = None
    siaddr = None
    giaddr = None
    chaddr = None

    sname = None
    file = None

    __magic_cookie = None

    def reset(self):
        self.op = DHCP_OP_REQ
        self.hw_type = 1
        self.hw_len = 6
        self.h_ops = 0
        self.xid = 0
        self.secs = 0
        self.flags = 0x8000

        self.ciaddr = bytes(4)
        self.yiaddr = bytes(4)
        self.siaddr = bytes(4)
        self.giaddr = bytes(4)

        self.chaddr = bytes(16)

        self.sname = bytes(64)
        self.file = bytes(128)

    def __init__(self):
        self.reset()
        self.__magic_cookie = 0x63825363
        self.my_init()

    def my_init(self):
        """重写这个方法
        """
        pass

    @property
    def magic_cookie(self):
        return self.__magic_cookie


class dhcp_parser(dhcp):
    def parse_options(self, byte_data: bytes):
        """解析DHCP options
        """
        results = []
        i = 0

        while 1:
            try:
                code = byte_data[i]
            except IndexError:
                raise DHCPErr("wrong DHCP packet")
            if 0 == code: continue
            if code == 0xff: break
            i += 1
            try:
                length = byte_data[i]
            except IndexError:
                raise DHCPErr("wrong DHCP packet")
            a = i + 1
            b = a + length

            data = byte_data[a:b]

            if len(data) != length:
                raise DHCPErr("wrong DHCP option length")
            results.append((code, length, data,))
            i = b
        return results

    def parse_public_header(self, public_data: bytes):
        try:
            self.op, self.hw_type, self.hw_len, self.h_ops, self.xid, self.secs, self.flags, \
                self.ciaddr, self.yiaddr, self.siaddr, self.giaddr, \
                self.chaddr, self.sname, self.file, magic_cookie = struct.unpack(HDR_FMT, public_data)
        except struct.error:
            raise DHCPErr("wrong DHCP data")

        if magic_cookie != self.magic_cookie:
            raise DHCPErr("wrong DHCP magic cookie")

    def my_init(self):
        pass

    def parse_from_link_data(self, link_data):
        dst_hwaddr, src_hwaddr, proto_type, ippkt = netpkt.parse_ether_data(link_data)
        if proto_type != 0x0800:
            raise DHCPErr("It is not IP protocol packet:%s" % hex(proto_type))
        src_addr, dst_addr, protocol, udpdata = netpkt.parse_ippkt(ippkt)
        if protocol != 17:
            raise DHCPErr("It is not UDP packet:%d" % protocol)
        src_port, dst_port, dhcpdata = netpkt.parse_udppkt(udpdata)
        self.parse_public_header(dhcpdata[0:HDR_LENGTH])
        options = self.parse_options(dhcpdata[HDR_LENGTH:])

        if dst_port == 67:
            is_server = True
        else:
            is_server = False

        r = (
            dst_hwaddr, src_hwaddr, dst_addr, src_addr, options, is_server,
        )

        return r


class dhcp_builder(dhcp):
    def my_init(self):
        pass

    def build(self, options: list):
        """options 格式为 [(code,byte_value),...]
        """
        try:
            pub_data = struct.pack(HDR_FMT,
                                   self.op,
                                   self.hw_type,
                                   self.hw_len,
                                   self.h_ops,
                                   self.xid,
                                   self.secs,
                                   self.flags,
                                   self.ciaddr,
                                   self.yiaddr,
                                   self.siaddr,
                                   self.giaddr,
                                   self.chaddr,
                                   self.sname,
                                   self.file,
                                   self.magic_cookie
                                   )
        except struct.error:
            raise DHCPErr("wrong DHCP data format")

        _list = []
        if len(self.chaddr) != 16:
            self.chaddr = self.chaddr + bytes(10)

        for code, byte_value in options:
            length = len(byte_value)

            try:
                x = struct.pack("!BB", code, length)
            except struct.error:
                raise DHCPErr("wrong option value")

            _list.append(x)
            _list.append(byte_value)

        _list.append(struct.pack("B", 0xff))
        opt_data = b"".join(_list)

        return b"".join([pub_data, opt_data, ])

    def build_to_link_data(self, dst_hwaddr: bytes, src_hwaddr: bytes, dst_ipaddr: bytes, src_ipaddr: bytes,
                           options: list, is_server=False):
        """
        :param dst_hwaddr:
        :param src_hwaddr:
        :param dst_ipaddr:
        :param src_ipaddr:
        :param options:
        :param is_server:是否是DHCP服务器报文
        :return:
        """
        if is_server:
            src_port, dst_port = (67, 68,)
        else:
            src_port, dst_port = (68, 67,)

        dhcp_data = self.build(options)
        udp_data = netpkt.build_udppkt(src_ipaddr, dst_ipaddr, src_port, dst_port, dhcp_data)
        ippkt = netpkt.build_ippkt(src_ipaddr, dst_ipaddr, 17, udp_data)
        link_data = netpkt.build_ether_data(dst_hwaddr, src_hwaddr, 0x0800, ippkt)

        return link_data

    def set_boot(self, server_name: str, filename: str):
        byte_s = filename.encode("iso-8859-1")
        if len(filename) > 127:
            raise ValueError("wrong filename length")
        filled = bytes(128 - len(byte_s))
        self.file = b"".join([byte_s, filled])

        byte_s = server_name.encode("iso-8859-1")
        if len(byte_s) > 63:
            raise ValueError("wrong server name length")
        filled = bytes(64 - len(byte_s))

        self.sname = b"".join([byte_s, filled])
