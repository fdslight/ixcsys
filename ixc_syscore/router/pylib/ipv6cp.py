#!/usr/bin/env python3

import time, random

import pywind.lib.netutils as netutils
import ixc_syscore.router.pylib.ncp as ncp
import ixc_syscore.router.pylib.lcp as lcp
import ixc_syslib.pylib.logging as logging


class IPv6CP(ncp.NCP):
    #__try_count = None
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

    def set_my_interface_id(self):
        mac_address = self.pppoe.runtime.wan_configs['public']['hwaddr']

        binary_mac = bin(int(mac_address[:2], 16))[2:].zfill(8)
        flipped_mac = binary_mac[:7] + "1" + binary_mac[8:]
        flipped_mac_hex = hex(int(flipped_mac, 2))[2:].zfill(2)
        eui64 = flipped_mac_hex + mac_address[2:6] + "FF:FE:" + mac_address[6:]

        self.__interface_id = netutils.str_hwaddr_to_bytes(eui64)

    def send_ncp_ipv6id_request(self):
        self.set_my_interface_id()
        #self.__try_count += 1
        self.__my_id = random.randint(1, 0xf0)
        data = self.build_opt_value(1, self.__interface_id)
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

        results = self.byte_to_hex(peer_id)
        logging.print_alert("PPPoE Peer Ipv6 interface ID: %s" % ":".join(results))

        self.send_ncp_packet(0x8057, lcp.CFG_ACK, _id, byte_data)

    def handle_cfg_ack(self, _id: int, byte_data: bytes):
        if len(byte_data) != 10: return
        if byte_data[1] != 10: return
        if byte_data[0] != 1: return

        if _id != self.__my_id: return

        self.__interface_id = byte_data[2:]
        #self.__try_count = 0

        results = self.byte_to_hex(self.__interface_id)
        logging.print_alert("PPPoE My Ipv6 interface ID: %s" % ":".join(results))

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
        if not self.pppoe.is_auth_ok(): return
        # if self.__try_count > 16:
        #    logging.print_alert("PPPoE IPv6CP server not response")
        #    return
        if not self.__interface_id:
            self.send_ncp_ipv6id_request()
            return

    def reset(self):
        #self.__try_count = 0
        self.__interface_id = b""
        self.__my_id = 0
