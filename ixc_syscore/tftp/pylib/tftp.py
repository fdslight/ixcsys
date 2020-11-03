#!/usr/bin/env python3

import struct

OP_RRQ = 1
OP_WRQ = 2
OP_DATA = 3
OP_ACK = 4
OP_ERR = 5
OP_OACK = 6

ERR_NOT_DEF = 0
ERR_FILE_NOT_FOUND = 1
ERR_ACS_VL = 2
ERR_DISK = 3
ERR_OP = 4
ERR_ID = 5
ERR_FILE_EXISTS = 6
ERR_NO_USER = 7

BLK_SIZE = 512


class TftpErr(Exception): pass


def build_extensions(seq: list):
    """
    :param seq,[(opt,value)...]
    """
    results = []
    for opt, val in seq:
        t = [opt.encode("iso-8859-1"), b"\0", val.encode("iso-8859-1"), b"\0"]
        results.append(b"".join(t))

    return b"".join(results)


def parse_extensions(ext_data: bytes):
    if not ext_data: return []
    results = {}
    name = ""
    value = ""
    flags = False

    while 1:
        if not ext_data: break
        p = ext_data.find(b"\0")
        if p < 0: break
        x = ext_data[0:p]
        if flags:
            value = x.decode("iso-8859-1")
            flags = False
            results[name] = value
        else:
            name = x.encode("iso-8859-1")
            flags = True
        p += 1
        ext_data = ext_data[p:]

    return results


def build_rrq_or_wrq_packet(op: int, filename: str, mode: str):
    seq = [struct.pack("!H", op), filename.encode("iso-8859-1"), bytes([0]), mode.encode(), bytes([0])]

    return b"".join(seq)


def build_data(block_num: int, data: bytes):
    seq = [struct.pack("!HH", OP_DATA, block_num), data]

    return b"".join(seq)


def build_ack(block_num: int):
    return struct.pack("!HH", OP_ACK, block_num)


def build_error(err_code: int, err_msg: str):
    seq = [struct.pack("!HH", OP_ERR, err_code)]
    seq.append(err_msg.encode())
    seq.append(bytes([0]))

    return b"".join(seq)


def parse_rrq_or_wrq_packet(byte_data: bytes):
    opcode, = struct.unpack("!H", byte_data[0:2])
    tmp_data = byte_data[2:]
    p = tmp_data.find(b"\0")

    if p <= 0:
        raise TftpErr("Wrong RRQ or WRQ packet format")

    filename = tmp_data[0:p].decode("iso-8859-1")
    p += 1
    tmp_data = tmp_data[p:]

    p = tmp_data.find(b"\0")
    if p <= 0:
        raise TftpErr("Wrong RRQ or WRQ packet format")

    mode = tmp_data[0:p]
    s_mode = mode.decode("iso-8859-1")

    if s_mode != "octet":
        raise TftpErr("only support octet mode")

    return opcode, (filename, s_mode,)


def parse_data_packet(byte_data: bytes):
    opcode, block_no = struct.unpack("!HH", byte_data[0:4])
    byte_data = byte_data[4:]

    return opcode, (block_no, byte_data,)


def parse_ack_packet(byte_data: bytes):
    if len(byte_data) != 4:
        raise TftpErr("Wrong ACK packet format")

    return struct.unpack("!HH", byte_data)


def parse_error_packet(byte_data: bytes):
    if len(byte_data) < 5:
        raise TftpErr("Wrong Error packet format")

    opcode, errcode = struct.unpack("!HH", byte_data[0:4])
    err_msg = ""

    byte_data = byte_data[4:]
    p = byte_data.find(b"\0")

    if p < 0:
        raise TftpErr("Wrong Error packet format")

    if p > 0:
        err_msg = byte_data[0:p].decode("iso-8859-1")

    return opcode, (errcode, err_msg,)


def parse(byte_data: bytes):
    size = len(byte_data)

    if size < 4: raise TftpErr("Wrong TFTP packet format")

    opcode, = struct.unpack("!H", byte_data[0:2])
    if opcode < 1 or opcode > 6: raise TftpErr("Wrong TFTP opcode value:%d" % opcode)

    if opcode == OP_WRQ or opcode == OP_RRQ:
        return parse_rrq_or_wrq_packet(byte_data)

    if opcode == OP_DATA:
        return parse_data_packet(byte_data)

    if opcode == OP_ACK:
        return parse_ack_packet(byte_data)

    if opcode == OP_ERR:
        return parse_error_packet(byte_data)

    return (opcode, None,)
