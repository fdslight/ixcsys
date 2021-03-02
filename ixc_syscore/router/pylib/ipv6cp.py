#!/usr/bin/env python3

import time, random

import ixc_syscore.router.pylib.ncp as ncp
import ixc_syscore.router.pylib.lcp as lcp
import ixc_syscore.router.pylib.router as router


class IPv6CP(ncp.NCP):
    __try_count = None
    __my_ipaddr_ok = None
    __my_ipaddr_subnet = None
    __my_id = None

    def my_init(self):
        self.reset()

    def send_ncp_ipv6addr_request(self):
        self.__try_count += 1
        self.__my_id = random.randint(1, 0xf0)
        data = self.build_opt_value(1, bytes(8))
        self.send_ncp_packet(ncp.PPP_IPv6CP, lcp.CFG_REQ, self.__my_id, data)

    def handle_cfg_request(self, _id: int, byte_data: bytes):
        """重写这个方法
        """
        self.send_ncp_packet(0x8057, lcp.CFG_ACK, _id, byte_data)

    def handle_cfg_ack(self, _id: int, byte_data: bytes):
        if len(byte_data) != 10: return
        if byte_data[1] != 10: return
        if byte_data[0] != 1: return

        if _id != self.__my_id: return

        self.__my_ipaddr_subnet = byte_data[2:]
        self.__my_ipaddr_ok = True
        self.__try_count = 0

        self.pppoe.runtime.router.netif_set_ip(router.IXC_NETIF_WAN, self.__my_ipaddr_subnet, 64, True)

    def handle_cfg_nak(self, _id: int, byte_data: bytes):
        if len(byte_data) != 10: return
        if byte_data[1] != 10: return
        if byte_data[0] != 1: return

        if _id != self.__my_id: return

        self.send_ncp_packet(ncp.PPP_IPv6CP, lcp.CFG_REQ, _id, byte_data)

    def handle_term_req(self, _id: int, byte_data: bytes):
        """重写这个方法
        """
        self.send_ncp_packet(ncp.PPP_IPCP, lcp.TERM_ACK, _id, byte_data)

    def start(self):
        self.send_ncp_ipv6addr_request()

    def loop(self):
        x = time.time() - self.up_time
        if x < 1: return
        if not self.__my_ipaddr_ok and self.__try_count > 3:
            return
        if not self.__my_ipaddr_ok:
            self.send_ncp_ipv6addr_request()
            return

    def reset(self):
        self.__try_count = 0
        self.__my_ipaddr_ok = False
        self.__my_ipaddr_subnet = None
        self.__my_id = 0
