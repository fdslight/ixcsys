#!/usr/bin/env python3

import struct, time
import ixc_syslib.pylib.logging as logging


class PAP(object):
    __pppoe = None
    __up_time = None
    __try_count = None
    __auth_ok = None

    def __init__(self, pppoe):
        self.__pppoe = pppoe
        self.reset()

    @property
    def debug(self):
        return self.__pppoe.debug

    def send_auth_request(self):
        self.__up_time = time.time()

        byte_user = self.__pppoe.runtime.pppoe_user.encode()
        byte_pass = self.__pppoe.runtime.pppoe_passwd.encode()

        size_a = len(byte_user)
        size_b = len(byte_pass)

        seq = [
            struct.pack("!B", size_a),
            byte_user,
            struct.pack("!B", size_b),
            byte_pass
        ]

        self.__pppoe.send_data_to_ns(0xc023, b"".join(seq))

    def handle_success(self):
        if self.debug: print("PPPoE PAP auth OK")

    def handle_fail(self, msg: bytes):
        logging.print_error("PPPoE PAP auth fail,msg:%s" % msg.decode("iso-8859-1"))
        self.__pppoe.reset()

    def handle_packet(self, code: int, _id: int, bye_data: bytes):
        if code not in (2, 3,): return
        if code == 2:
            self.handle_success()
        else:
            self.handle_fail(bye_data)

    def loop(self):
        now = time.time() - self.__up_time

        if now < 1: return
        if not self.__auth_ok: self.send_auth_request()

    def reset(self):
        self.__up_time = time.time()
        self.__try_count = 0
        self.__auth_ok = False
