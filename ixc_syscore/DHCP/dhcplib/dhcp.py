#!/usr/bin/env python3

import struct, random

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

    def __init__(self):
        self.op = DHCP_OP_REQ
        self.hw_type = 1
        self.hw_len = 6
        self.h_ops = 0
        self.xid = random.randint(1, 0xfffffffe)
        self.secs = 0
        self.flags = 0

        self.ciaddr = bytes(4)
        self.yiaddr = bytes(4)
        self.siaddr = bytes(4)
        self.giaddr = bytes(4)

        self.chaddr = bytes(16)

        self.sname = bytes(64)
        self.file = bytes(128)

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
        for code, byte_value in options:
            length = len(byte_value)

            try:
                x = struct.pack("!BB", code, length)
            except struct.error:
                raise DHCPErr("wrong option value")

            _list.append(x)
            _list.append(byte_value)

        _list.append(struct.pack("!I", self.magic_cookie))

        opt_data = b"".join(_list)

        return b"".join([pub_data, opt_data, ])
