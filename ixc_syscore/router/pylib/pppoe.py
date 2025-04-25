#!/usr/bin/env python3
import struct, time

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

    __ac_names = None

    # pppoe是否认证成功
    __auth_ok = None
    __time = None
    __selected_ac_name = None
    __selected_ac_count = None

    __ac_names_time = None

    __is_first = None

    def __init__(self, runtime):
        self.__runtime = runtime
        self.__start = False
        self.__lcp = lcp.LCP(self)
        self.__chap = chap.CHAP(self)
        self.__pap = pap.PAP(self)
        self.__ipcp = ipcp.IPCP(self)
        self.__ipv6cp = ipv6cp.IPv6CP(self)
        self.__time = time.time()

        self.__ac_names = []
        self.__auth_ok = False
        self.__selected_ac_name = ""
        self.__selected_ac_count = 0
        self.__ac_names_time = time.time()
        self.__is_first = False

    @property
    def router(self):
        return self.__runtime.router

    @property
    def debug(self):
        return self.__runtime.debug

    @property
    def runtime(self):
        return self.__runtime

    @property
    def lcp(self):
        return self.__lcp

    @property
    def ipcp(self):
        return self.__ipcp

    def start_lcp(self):
        self.__start = True
        self.__lcp.start_lcp()
        self.__time = time.time()

    def stop_lcp(self):
        self.__start = False
        self.__lcp.reset()
        self.__ipcp.reset()
        self.__ipv6cp.reset()
        self.__chap.reset()
        self.__pap.reset()

        logging.print_alert("PPPoE LCP STOP and reset")

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
            return

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
        self.__start = False

        if self.__is_first:
            self.__is_first = False
        else:
            # 尝试该表pppoe server进行协商,多个pppoe server可能个别存在问题
            self.change_ac_server()

        # 避免在lcp,lpcp...中调用self.reset()方法,会导致死循环
        self.__lcp.reset()
        self.__ipcp.reset()
        self.__ipv6cp.reset()
        self.__chap.reset()
        self.__pap.reset()

        self.__runtime.router.pppoe_reset()

        logging.print_alert("PPPoE reset")

    def loop(self):
        now = time.time()
        if not self.__start: return
        self.__lcp.loop()
        if not self.__lcp.lcp_ok(): return
        if self.__lcp.auth_method_get() == "pap": self.__pap.loop()
        # 一小时清理ac清单一次
        if now - self.__ac_names_time > 3600:
            self.__ac_names = []
            self.__ac_names_time = now
        # 超过30秒还未认证成功那么更改AC进行认证
        if now - self.__time >= 30 and not self.is_auth_ok():
            self.reset()
            logging.print_alert("PPPoE auth handshake timeout with ac %s" % self.__selected_ac_name)
            return
        if not self.is_auth_ok(): return

        self.__ipcp.loop()
        self.__ipv6cp.loop()

    def ncp_start(self):
        self.__ipcp.start()
        self.__ipv6cp.start()

    def record_ac_name(self, ac_name: str):
        """记录AC name
        """
        if ac_name not in self.__ac_names:
            # 超过256个ac那么不记录,避免记录过多浪费内存,过多的ac name可能存在网络攻击,不限制会导致内存被占用过多导致系统内存不足
            if len(self.__ac_names) > 256: return
            self.__ac_names.append(ac_name)
        return

    def is_auth_ok(self):
        return self.__auth_ok

    def set_auth_ok(self, auth_ok: bool):
        self.__auth_ok = auth_ok

    def tell_selected_ac_name(self, ac_name: str):
        """系统选择的AC name
        """
        self.__selected_ac_name = ac_name
        logging.print_alert("PPPoE Client select ac name %s" % ac_name)

    def change_ac_server(self):
        if not self.__ac_names:
            logging.print_alert("no found avaliable ac for change ac server")
            return

        ac_len = len(self.__ac_names)

        self.__selected_ac_count += 1
        # 如果超过ac清单,那么从头开始认证
        if self.__selected_ac_count == ac_len:
            self.__selected_ac_count = 0

        ac_name = self.__ac_names[self.__selected_ac_count]
        self.runtime.router.pppoe_force_ac_name(ac_name, True)

        logging.print_alert("PPPoE Client change ac name to %s" % ac_name)

    def current_ac_name_get(self):
        return self.__selected_ac_name
