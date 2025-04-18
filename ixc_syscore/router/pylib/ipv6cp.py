#!/usr/bin/env python3

import time, random

import ixc_syscore.router.pylib.ncp as ncp
import ixc_syscore.router.pylib.lcp as lcp
import router


class IPv6CP(ncp.NCP):
    __try_count = None
    __interface_id = None
    __peer_id = None
    __my_id = None

    def byte_to_hex(self, byte_data: bytes):
        results = []
        for n in byte_data:
            ch = hex(n)[2:].lower()
            results.append(ch)

        return results

    def my_init(self):
        self.reset()

    def send_ncp_ipv6id_request(self):
        self.__try_count += 1
        self.__my_id = random.randint(1, 0xf0)
        data = self.build_opt_value(1, bytes(8))
        self.send_ncp_packet(ncp.PPP_IPv6CP, lcp.CFG_REQ, self.__my_id, data)

    def handle_cfg_request(self, _id: int, byte_data: bytes):
        """重写这个方法
        """
        if byte_data[0] != 1: return
        if byte_data[1] != 10: return

        peer_id = byte_data[2:]
        if len(peer_id) != 8: return

        # 此处检查对端interface id是否合法
        """
        should_peer_id = b""
        
        if should_peer_id != peer_id:
            self.send_ncp_packet(0x8057, lcp.CFG_NAK, _id, should_peer_id)
            return
        """

        if self.debug:
            results = self.byte_to_hex(peer_id)
            print("PPPoE Peer Ipv6 interface ID: %s" % ":".join(results))

        self.send_ncp_packet(0x8057, lcp.CFG_ACK, _id, byte_data)

    def handle_cfg_ack(self, _id: int, byte_data: bytes):
        if len(byte_data) != 10: return
        if byte_data[1] != 10: return
        if byte_data[0] != 1: return

        if _id != self.__my_id: return

        self.__interface_id = byte_data[2:]
        self.__try_count = 0

        if self.debug:
            results = self.byte_to_hex(self.__interface_id)
            print("PPPoE My Ipv6 interface ID: %s" % ":".join(results))
        ''''''

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
        self.send_ncp_ipv6id_request()

    def loop(self):
        if not self.__interface_id and self.__try_count > 3:
            return
        if not self.__interface_id:
            self.send_ncp_ipv6id_request()
            return

    def reset(self):
        self.__try_count = 0
        self.__interface_id = False
        self.__my_id = 0
