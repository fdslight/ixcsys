#!/usr/bin/env python3

import struct, time
import ixc_syscore.router.pylib.lcp as lcp
import ixc_syslib.pylib.logging as logging

PPP_IPv6CP = 0x8057
PPP_IPCP = 0x8021


class NCP(object):
    __pppoe = None
    __fn_set = None
    __up_time = None

    def __init__(self, pppoe):
        self.__pppoe = pppoe
        self.__up_time = time.time()
        self.__fn_set = {
            lcp.CFG_REQ: self.handle_cfg_request,
            lcp.CFG_ACK: self.handle_cfg_ack,
            lcp.CFG_NAK: self.handle_cfg_nak,
            lcp.CFG_REJECT: self.handle_cfg_reject,
            lcp.TERM_REQ: self.handle_term_req,
            lcp.TERM_ACK: self.handle_term_ack,
            lcp.CODE_REJECT: self.handle_code_reject
        }

    def my_init(self):
        """重写这个方法
        """
        pass

    def send_ncp_packet(self, ppp_proto: int, code: int, _id: int, byte_data: bytes):
        if ppp_proto not in (PPP_IPCP, PPP_IPv6CP,):
            raise ValueError("cannot permit ppp protocol value %s" % hex(ppp_proto))
        length = len(byte_data) + 4
        header = struct.pack("!bbH", code, _id, length)
        data = b"".join([header, byte_data])
        self.__up_time = time.time()
        self.__pppoe.send_data_to_ns(ppp_proto, data)

    def handle_cfg_request(self, _id: int, byte_data: bytes):
        """重写这个方法
        """
        logging.print_error("server cannot send NCP request packet")

    def handle_cfg_ack(self, _id: int, byte_data: bytes):
        """重写这个方法
        """
        pass

    def handle_cfg_nak(self, _id: int, byte_data: bytes):
        """重写这个方法
        """
        pass

    def handle_cfg_reject(self, _id: int, byte_data: bytes):
        """重写这个方法
        """
        logging.print_error("server cfg_reject NCP request packet")

    def handle_term_req(self, _id: int, byte_data: bytes):
        """重写这个方法
        """
        pass

    def handle_term_ack(self, _id: int, byte_data: bytes):
        """重写这个方法
        """
        pass

    def handle_code_reject(self, _id: int, byte_data: bytes):
        """重写这个方法
        """
        logging.print_error("server code_reject NCP request packet")

    def handle_packet(self, code: int, _id: int, byte_data: bytes):
        if code < 1 or code > 7: return
        if code not in self.__fn_set:
            logging.print_error("not found code %d function map for NCP" % code)
            return
        self.__fn_set[code](_id, byte_data)

    @property
    def debug(self):
        return self.__pppoe.debug

    @property
    def pppoe(self):
        return self.__pppoe

    @property
    def up_time(self):
        return self.__up_time

    def build_opt_value(self, _type: int, value: bytes):
        """构建选项值
        """
        length = len(value) + 2
        header = struct.pack("!bb", _type, length)

        return b"".join([header, value])