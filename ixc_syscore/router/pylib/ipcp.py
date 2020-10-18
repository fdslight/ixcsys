#!/usr/bin/env python3
import random

import ixc_syscore.router.pylib.ncp as ncp
import ixc_syscore.router.pylib.lcp as lcp

import ixc_syslib.pylib.logging as logging


class IPCP(ncp.NCP):
    __my_id = None
    __ipaddr_ok = None
    __my_ipaddr = None

    def my_init(self):
        self.__my_id = 0
        self.__ipaddr_ok = False

    def parse_options(self, cfg_data: bytes):
        permits = (
            2, 3,
        )
        results = []
        if len(cfg_data) < 2: return results
        idx = 0
        while 1:
            try:
                _type = cfg_data[idx]
                length = cfg_data[idx + 1]
            except IndexError:
                results = []
                if self.debug: print("Wrong IPCP configure data")
                break
            idx += 2
            e = idx + length
            opt_data = cfg_data[idx:e]
            if len(opt_data) != length:
                results = []
                if self.debug: print("Wrong IPCP option length field value")
                break
            if _type not in permits:
                results = []
                if self.debug: print("unkown IPCP option type %d" % _type)
                break

            if _type == 2 and length < 4:
                results = []
                if self.debug: print("Wrong data length for IPCP type %d" % _type)
                return

            if _type == 3 and length != 6:
                results = []
                if self.debug: print("Wrong data length for IPCP type %d" % _type)
                return

            results.append((_type, opt_data,))

        return results

    def send_ncp_ipaddr_request(self):
        """发送NCP的IP地址请求
        """
        self.__my_id = random.randint(1, 0xf0)
        sent_data = self.build_opt_value(3, bytes([0x00, 0x00, 0x00, 0x00]))
        self.send_ncp_packet(ncp.PPP_IPCP, lcp.CFG_REQ, self.__my_id, sent_data)

    def handle_cfg_ack(self, _id: int, byte_data: bytes):
        """重写这个方法
        """
        options = self.parse_options(byte_data)
        if not options: return

        for _type, value in options:
            if _type == 2:
                logging.print_error("PPPOE server IPCP bug,client not send configure request for type %d" % _type)
                return
            if _type == 3:
                self.__my_ipaddr = value
                self.__ipaddr_ok = True
                break
            ''''''
        return

    def handle_cfg_nak(self, _id: int, byte_data: bytes):
        """重写这个方法
        """
        options = self.parse_options(byte_data)
        if not options: return

        rejects = []
        requests = []

        for _type, value in options:
            if _type == 2:
                rejects.append(self.build_opt_value(_type, value))
                continue
            if _type == 3:
                requests.append(self.build_opt_value(_type, value))
                continue
            ''''''
        if rejects:
            self.send_ncp_packet(ncp.PPP_IPCP, lcp.CFG_REJECT, _id, b"".join(rejects))
        if requests:
            self.__my_id = random.randint(1, 0xf0)
            self.send_ncp_packet(ncp.PPP_IPCP, lcp.CFG_REQ, self.__my_id, b"".join(requests))
        return

    def handle_term_req(self, _id: int, byte_data: bytes):
        """重写这个方法
        """
        self.send_ncp_packet(ncp.PPP_IPCP, lcp.TERM_ACK, _id, byte_data)

    def handle_term_ack(self, _id: int, byte_data: bytes):
        """重写这个方法
        """
        pass
