#!/usr/bin/env python3
"""局域网唤醒
"""
import socket


class wake_on_lan(object):
    """用来唤醒局域网的机器
    """
    __s = None

    def __init__(self, bind_ip="0.0.0.0"):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.bind((bind_ip, 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.__s = s

    def wake(self, dst_mac):
        magic_pkt = self.__gen_magic_packet(dst_mac)
        if not magic_pkt: return

        self.__s.sendto(magic_pkt, ("255.255.255.255", 7,))

    def __gen_magic_packet(self, hwaddr):
        """生成magic包
        :param hwaddr:
        :return:
        """
        a = [255, 255, 255, 255, 255, 255]
        byte_a = bytes(a)

        a = []
        seq = hwaddr.split(":")

        if len(seq) != 6: return None

        for s in seq:
            v = int("0x%s" % s, 16)
            a.append(v)
        b = bytes(a)
        b = b * 16

        return b"".join([byte_a, b])

    def release(self):
        self.__s.close()
