#!/usr/bin/env python3
import socket


class IPv6CP(object):
    __pppoe = None

    def __init__(self, pppoe):
        self.__pppoe = pppoe

    def handle_packet(self, code: int, _id: int, byte_data: bytes):
        pass
