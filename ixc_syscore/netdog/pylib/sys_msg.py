#!/usr/bin/env python3
import struct, time, socket

RULE_ALERT = 0
RULE_ADD = 3
RULE_DEL = 4


class SYS_MSG_Error(Exception):
    pass


def wrap_sys_msg(_type: int, msg: bytes):
    if _type < 0 or _type > 0xff:
        raise ValueError("wrong _type value")

    wrap_msg = [
        struct.pack("!BB6s", 1, _type, bytes(6)),
        msg
    ]

    return b"".join(wrap_msg)


def unwrap_sys_msg(msg: bytes):
    try:
        ver, _type, _ = struct.unpack("!BB6s", msg[0:8])
    except struct.error:
        raise SYS_MSG_Error("wrong message")

    return _type, msg[8:]


def get_pkt_mon_port():
    """获取网络包监控端口
    """
    msg = wrap_sys_msg(1, b"")

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(2)
    s.connect(("127.0.0.1", 8965))
    s.send(msg)

    resp_msg = s.recv(1024)
    s.close()
    print(len(resp_msg))
    _type, msg = unwrap_sys_msg(msg)
    key, port = struct.unpack("!16sH", msg)

    return key, port
