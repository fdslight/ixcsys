#!/usr/bin/env python3
import struct

import ixc_syscore.router.pylib.lcp as lcp
import ixc_syscore.router.pylib.ipcp as ipcp
import ixc_syscore.router.pylib.ipv6cp as ipv6cp


class pppoe(object):
    __runtime = None
    __lcp = None

    __ipcp = None
    __ipv6cp = None

    def __init__(self, runtime):
        self.__runtime = runtime
        self.__lcp = lcp.LCP(self)
        self.__ipcp = ipcp.IPCP(self)
        self.__ipv6cp = ipv6cp.IPv6CP(self)
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
        if protocol == 0xc023:
            self.handle_pap_from_ns(data)
        if protocol == 0xc223:
            self.handle_chap_from_ns(data)
        if protocol == 0x8021:
            self.handle_ipcp_from_ns(data)
        if protocol == 0x8057:
            self.handle_ipv6cp_from_ns(data)

    def handle_chap_from_ns(self, data: bytes):
        pass

    def handle_pap_from_ns(self, data: bytes):
        pass

    def handle_ipcp_from_ns(self, data: bytes):
        if len(data) < 4: return
        size = len(data)
        code, _id, length = struct.unpack("!bbH", data[0:4])

        if length != size:
            if self.debug: print("Wrong IPCP length field value")
            return
        data = data[4:]
        self.__ipcp.handle_packet(code, _id, data)

    def handle_ipv6cp_from_ns(self, data: bytes):
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
