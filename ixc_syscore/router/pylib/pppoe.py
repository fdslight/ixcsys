#!/usr/bin/env python3

class pppoe(object):
    __runtime = None

    def __init__(self, runtime):
        self.__runtime = runtime

    def send_data_to_ns(self, protocol: int, byte_data: bytes):
        """发送数据到协议栈
        """
        pass

    def handle_packet_from_ns(self, protocol: int, data: bytes):
        """处理来自于协议栈的数据
        """
        pass

    def handle_chap_from_ns(self, data: bytes):
        pass

    def handle_pap_from_ns(self, data: bytes):
        pass

    def handle_lcp_from_ns(self, data: bytes):
        pass
