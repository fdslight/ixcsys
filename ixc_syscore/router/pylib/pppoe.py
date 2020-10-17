#!/usr/bin/env python3
import struct

import ixc_syscore.router.pylib.lcp as lcp


class pppoe(object):
    __runtime = None
    __lcp = None

    def __init__(self, runtime):
        self.__runtime = runtime
        self.__lcp = lcp.LCP(self)
        self.__runtime.router.set_pppoe_session_packet_recv_fn(self.handle_packet_from_ns)

    @property
    def debug(self):
        return self.__runtime.debug

    def start_lcp(self):
        self.__lcp.start_lcp()

    def send_data_to_ns(self, protocol: int, byte_data: bytes):
        """发送数据到协议栈
        :param protocol,PPP协议
        :param byte_data,数据
        """
        self.__runtime.router.pppoe_data_send(protocol, byte_data)

    def handle_packet_from_ns(self, protocol: int, data: bytes):
        """处理来自于协议栈的数据
        """
        if protocol == 0xc021:
            self.handle_lcp_from_ns(data)

    def handle_chap_from_ns(self, data: bytes):
        pass

    def handle_pap_from_ns(self, data: bytes):
        pass

    def handle_lcp_from_ns(self, data: bytes):
        if len(data) < 4: return
        size = len(data)
        code, _id, length = struct.unpack("!bbH", data[0:4])

        if length != size:
            if self.debug: print("Wrong LCP length field value")
            return
        data = data[4:]
        self.__lcp.handle_packet(code, _id, data)

    def reset(self):
        self.__runtime.router.pppoe_reset()
