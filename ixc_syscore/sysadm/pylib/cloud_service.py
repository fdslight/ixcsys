#!/usr/bin/env python3
"""云服务通信协议
version:1 byte
frame_type:1 byte 数据帧类型
reserve:2 bytes 保留字节
tot_length:4 bytes
user_key:16 bytes

content
"""

DATA_TYPE_NON = 0
DATA_TYPE_PING = 1
DATA_TYPE_PONG = 2
DATA_TYPE_RPC_REQ = 3
DATA_TYPE_RPC_RESP = 4

import sys, hashlib, os, struct

import pywind.lib.reader as reader


def calc_str_md5(s: str):
    md5 = hashlib.md5()
    md5.update(s.encode())

    return md5.digest()


def calc_bytes_md5(byte_data: str):
    md5 = hashlib.md5()
    md5.update(byte_data)

    return md5.digest()


class ProtocolErr(Exception):
    pass


class parser(object):
    __byte_key = None
    __results = None
    __reader = None
    __header_ok = None
    __content_length = None
    __type = None

    def __init__(self, key: str):
        self.__byte_key = calc_str_md5(key)
        self.__results = []
        self.__reader = reader.reader()
        self.__header_ok = False
        self.__content_length = 0

    def __parse_header(self):
        if self.__reader.size() < 24: return

        _, _type, _, tot_len, key = struct.unpack("!BBHI16s", self.__reader.read(24))
        if key != self.__byte_key:
            raise ProtocolErr("auth failed")

        if tot_len < 24:
            raise ProtocolErr("wrong header total length")

        self.__content_length = tot_len - 24
        self.__type = _type
        self.__header_ok = True

    def __parse_body(self):
        if self.__reader.size() < self.__content_length: return

        self.__results.append(
            (self.__type, self.__reader.read(self.__content_length),)
        )
        self.__header_ok = False

    def parse(self, byte_data: bytes):
        if byte_data: self.__reader._putvalue(byte_data)

        if not self.__header_ok:
            self.__parse_header()
        if not self.__header_ok: return
        self.__parse_body()

    def get_result(self):
        try:
            return self.__results.pop(0)
        except IndexError:
            return None


class builder(object):
    __byte_key = None

    def __init__(self, key: str):
        self.__byte_key = calc_str_md5(key)

    def build_header(self, _type: int, data_len: int):
        tot_len = data_len + 24
        r = struct.pack("!BBHI16s", 1, _type, 0, tot_len, self.__byte_key)

        return r

    def wrap_data(self, _type: int, byte_data: bytes):
        data_len = len(byte_data)

        header_data = self.build_header(_type, data_len)

        return b"".join([header_data, byte_data])


"""
p = parser("hello")
b = builder("hello")

data = b.wrap_data(DATA_TYPE_NON, b"hello,world")
p.parse(data)

print(p.get_result())
"""
