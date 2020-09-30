#!/usr/bin/env python3

"""TCP/IP构建以及解析
"""

import struct, random


class NetPktErr(Exception): pass


def csum_calc(packet: bytes):
    """计算csum
    """
    size = len(packet)
    checksum = 0
    a = 0
    b = 1
    while size > 1:
        checksum += (packet[a] << 8) | packet[b]
        size -= 2
        a += 2
        b += 2

    if size:
        checksum += (packet[a] << 8)

    checksum = (checksum >> 16) + (checksum & 0xffff)
    checksum += (checksum >> 16)

    return (~checksum) & 0xffff


def build_ether_data(dst_hwaddr: bytes, src_hwaddr: bytes, link_proto: int, byte_data: bytes):
    """构建以太网数据包
    """
    header_data = struct.pack("!6s6sH", dst_hwaddr, src_hwaddr, link_proto)

    return b"".join([header_data, byte_data])


def parse_ether_data(byte_data: bytes):
    """解析以太网数据包
    """
    if len(byte_data) < 14:
        raise NetPktErr("wrong ethernet packet")

    dst_hwaddr, src_hwaddr, proto = struct.unpack("!6s6sH", byte_data[0:14])
    r = (dst_hwaddr, src_hwaddr, proto, byte_data[14:],)

    return r


def build_udppkt(src_ipaddr: bytes, dst_ipaddr: bytes, src_port: int, dst_port: int, payload_data: bytes,
                 is_ipv6=False):
    """构建UDP数据包
    """
    length = len(payload_data) + 8
    header = struct.pack("!HHHH", src_port, dst_port, length, 0)
    udp_data = b"".join([header, payload_data])

    # 伪头部
    if not is_ipv6:
        ps_hdr = struct.pack("!4s4sBBH", src_ipaddr, dst_ipaddr, 0, 17, length)
    else:
        ps_hdr = struct.pack("!16s16sBBH", src_ipaddr, dst_ipaddr, 0, 17, length)
    tmp_data = b"".join([ps_hdr, udp_data])

    csum = csum_calc(tmp_data)

    _list = list(udp_data)

    _list[6] = (csum & 0xff00) >> 8
    _list[7] = csum & 0x00ff

    return bytes(_list)


def build_ippkt(src_ipaddr: bytes, dst_ipaddr: bytes, protocol: int, payload_data: bytes):
    """构建IP数据包
    """
    header = struct.pack("!BBHHHBBH4s4s",
                         0x45, 0, len(payload_data) + 20,
                         random.randint(1, 0xfffe), 0b0100_0000_0000_0000,
                         64, protocol, 0,
                         src_ipaddr, dst_ipaddr
                         )
    csum = csum_calc(header)

    _list = list(header)

    _list[10] = (csum & 0xff00) >> 8
    _list[11] = csum & 0xff

    return b"".join([bytes(_list), payload_data])


def parse_ippkt(byte_data: bytes):
    size = len(byte_data)
    hdr_len = (byte_data[0] & 0x0f) * 4

    if size < hdr_len:
        raise NetPktErr("wrong data length")

    payload_data = byte_data[hdr_len:]

    r = (byte_data[12:16], byte_data[16:20], byte_data[9], payload_data,)

    return r


def parse_udppkt(udp_data: bytes):
    if len(udp_data) < 9: return NetPktErr("wrong UDP packet")

    src_port, dst_port, length, csum = struct.unpack("!HHHH", udp_data[0:8])
    r = (src_port, dst_port, udp_data[8:],)

    return r


def arp_build(op: int, src_hwaddr: bytes, dst_hwaddr: bytes, src_ipaddr: bytes, dst_ipaddr: bytes):
    """构建ARP数据包
    """
    try:
        rs = struct.pack("!HHBBH6s4s6s4s", 1, 0x0800, 6, 4, op, src_hwaddr, src_ipaddr, dst_hwaddr, dst_ipaddr)
    except struct.error:
        return None
    return rs


def arp_parse(arp_data: bytes):
    """解析ARP数据包
    """
    arp_data = arp_data[0:28]
    try:
        return struct.unpack("!HHBBH6s4s6s4s", arp_data)
    except struct.error:
        return None
