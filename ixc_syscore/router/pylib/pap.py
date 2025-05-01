#!/usr/bin/env python3
import os
import struct, time
import ixc_syslib.pylib.logging as logging


class PAP(object):
    __pppoe = None
    __up_time = None
    __try_count = None
    __auth_ok = None
    __pap_id = None

    def __init__(self, pppoe):
        self.__pppoe = pppoe
        self.__pap_id = 0
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

        t = os.urandom(1)
        self.__pap_id = t[0]
        z = b"".join(seq)
        length = len(z) + 4
        sent_data = struct.pack("!B", 1) + t + struct.pack("!H", length) + z

        self.__pppoe.send_data_to_ns(0xc023, sent_data)

    def handle_success(self):
        self.__pppoe.ncp_start()
        self.__pppoe.set_auth_ok(True)
        self.__pppoe.router.pppoe_set_ok(True)

        logging.print_alert("PPPoE PAP auth OK")

    def handle_fail(self, msg: bytes):
        logging.print_alert("PPPoE PAP auth fail,msg:%s" % msg.decode("iso-8859-1"))
        self.__pppoe.reset()

    def handle_packet(self, code: int, _id: int, bye_data: bytes):
        if code not in (2, 3,):
            logging.print_alert("PPPoE wrong pap auth code")
            return
        if _id != self.__pap_id:
            logging.print_alert("PPPoE wrong pap id response")
            return
        if code == 2:
            self.handle_success()
        else:
            self.handle_fail(bye_data)

    def loop(self):
        now = time.time() - self.__up_time

        if now < 1: return
        if not self.__pppoe.is_auth_ok():
            logging.print_alert("PPPoE send PAP auth request")
            self.send_auth_request()

    def reset(self):
        self.__up_time = time.time()
        self.__try_count = 0
        self.__auth_ok = False
