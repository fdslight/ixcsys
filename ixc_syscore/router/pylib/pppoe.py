#!/usr/bin/env python3
import struct

import ixc_syscore.router.pylib.lcp as lcp
import ixc_syscore.router.pylib.ipcp as ipcp
import ixc_syscore.router.pylib.ipv6cp as ipv6cp
import ixc_syscore.router.pylib.chap as chap
import ixc_syscore.router.pylib.pap as pap

import ixc_syslib.pylib.logging as logging


class pppoe(object):
    __runtime = None
    __start = None
    __lcp = None
    __chap = None
    __pap = None

    __ipcp = None
    __ipv6cp = None

    def __init__(self, runtime):
        self.__runtime = runtime
        self.__start = False
        self.__lcp = lcp.LCP(self)
        self.__chap = chap.CHAP(self)
        self.__pap = pap.PAP(self)
        self.__ipcp = ipcp.IPCP(self)
        self.__ipv6cp = ipv6cp.IPv6CP(self)

    @property
    def debug(self):
        return self.__runtime.debug

    @property
    def runtime(self):
        return self.__runtime

    @property
    def lcp(self):
        return self.__lcp

    def start_lcp(self):
        self.__start = True
        self.__lcp.start_lcp()

    def stop_lcp(self):
        self.__start = False
        self.__lcp.reset()
        self.__ipcp.reset()
        self.__ipv6cp.reset()
        self.__chap.reset()
        self.__pap.reset()

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
            return
        # 如果LCP没有协商成功那么丢弃数据包
        if not self.__lcp.lcp_ok(): return
        if protocol == 0xc023 and self.__lcp.auth_method_get() != "pap":
            logging.print_error("PPPoE Server bug,PAP auth packet but LCP neg is not pap")
            return
        if protocol == 0xc223 and self.__lcp.auth_method_get() != "chap":
            logging.print_error("PPPoE Server bug,PAP auth packet but LCP neg is not pap")
            return
        if protocol == 0xc023:
            self.handle_pap_from_ns(data)
            return
        if protocol == 0xc223:
            self.handle_chap_from_ns(data)
            return
        if protocol == 0x8021:
            self.handle_ipcp_from_ns(data)
            return
        if protocol == 0x8057:
            self.handle_ipv6cp_from_ns(data)

    def handle_chap_from_ns(self, data: bytes):
        if len(data) < 4: return
        size = len(data)
        code, _id, length = struct.unpack("!BBH", data[0:4])

        if length != size:
            if self.debug: print("Wrong CHAP length field value")
            return
        data = data[4:]
        self.__chap.handle_packet(code, _id, data)

    def handle_pap_from_ns(self, data: bytes):
        if len(data) < 4: return
        size = len(data)
        code, _id, length = struct.unpack("!BBH", data[0:4])

        if length != size:
            if self.debug: print("Wrong PAP length field value")
            return
        data = data[4:]
        self.__pap.handle_packet(code, _id, data)

    def handle_ipcp_from_ns(self, data: bytes):
        if len(data) < 4: return
        size = len(data)
        code, _id, length = struct.unpack("!BBH", data[0:4])

        if length != size:
            if self.debug: print("Wrong IPCP length field value")
            return
        data = data[4:]
        self.__ipcp.handle_packet(code, _id, data)

    def handle_ipv6cp_from_ns(self, data: bytes):
        if len(data) < 4: return
        size = len(data)
        code, _id, length = struct.unpack("!BBH", data[0:4])

        if length != size:
            if self.debug: print("Wrong IPv6CP length field value")
            return
        data = data[4:]
        self.__ipv6cp.handle_packet(code, _id, data)

    def handle_lcp_from_ns(self, data: bytes):
        if len(data) < 4: return
        size = len(data)
        code, _id, length = struct.unpack("!BBH", data[0:4])

        if length != size:
            if self.debug: print("Wrong LCP length field value")
            return
        data = data[4:]
        self.__lcp.handle_packet(code, _id, data)

    def reset(self):
        # 注意这里不能条用self.__lcp.reset(),避免可能循环调用
        self.__runtime.router.pppoe_reset()
        self.__lcp.reset()
        self.__ipcp.reset()
        self.__ipv6cp.reset()
        self.__chap.reset()
        self.__pap.reset()

    def loop(self):
        if not self.__start: return
        self.__lcp.loop()
        if not self.__lcp.lcp_ok(): return

        self.__ipcp.loop()
        self.__ipv6cp.loop()

        if self.__lcp.auth_method_get() == "pap": self.__pap.loop()

    def ncp_start(self):
        self.__ipcp.start()
        self.__ipv6cp.start()
