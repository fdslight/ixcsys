#!/usr/bin/env python3

import hashlib, struct

import ixc_syslib.pylib.logging as logging


class PAP(object):
    __pppoe = None

    def __init__(self, pppoe):
        self.__pppoe = pppoe

    @property
    def debug(self):
        return self.__pppoe.debug

    def handle_packet(self, code: int, _id: int, bye_data: bytes):
        pass
