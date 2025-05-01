#!/usr/bin/env python3
import hashlib, struct

import ixc_syslib.pylib.logging as logging


class CHAP(object):
    __pppoe = None

    def __init__(self, pppoe):
        self.__pppoe = pppoe

    @property
    def debug(self):
        return self.__pppoe.debug

    def handle_challenge(self, _id: int, byte_data: bytes):
        size = len(byte_data)
        if size < 1:
            if self.debug: print("Wrong challenge data for PPPoE chap")
            return
        value_size = byte_data[0]
        byte_data = byte_data[1:]

        if len(byte_data) < value_size:
            if self.debug: print("PPPoE server bug,wrong value size for chap")
            self.__pppoe.reset()
            return

        value = byte_data[0:value_size]
        name = byte_data[value_size:]

        # 构建数据包
        byte_user = self.__pppoe.runtime.pppoe_user.encode()
        byte_pass = self.__pppoe.runtime.pppoe_passwd.encode()

        md5 = hashlib.md5(bytes([_id]) + byte_pass + value).digest()
        length = 4 + 1 + 16 + len(byte_user)

        header = struct.pack("!BBH", 2, _id, length)
        seq = [
            header, bytes([16]), md5, byte_user
        ]
        self.__pppoe.send_data_to_ns(0xc223, b"".join(seq))

    def handle_success(self, _id: int, byte_data: bytes):
        self.__pppoe.ncp_start()
        self.__pppoe.router.pppoe_set_ok(True)

        self.__pppoe.set_auth_ok(True)
        logging.print_alert("PPPoE chap auth OK")

    def handle_failure(self, _id: int, byte_data: bytes):
        if byte_data:
            s = byte_data.decode("iso-8859-1")
        else:
            s = ""
        logging.print_alert("PPPoE chap auth failure,server msg:%s" % s)
        self.__pppoe.reset()

    def handle_packet(self, code: int, _id: int, bye_data: bytes):
        if code not in (1, 3, 4,): return
        if code == 1:
            self.handle_challenge(_id, bye_data)
            return
        if code == 4:
            self.handle_failure(_id, bye_data)
            return
        self.handle_success(_id, bye_data)

    def loop(self):
        pass

    def reset(self):
        pass
