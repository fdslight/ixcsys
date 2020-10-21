#!/usr/bin/env python3
import random, socket, time

import ixc_syscore.router.pylib.ncp as ncp
import ixc_syscore.router.pylib.lcp as lcp

import ixc_syscore.router.pylib.router as router

import ixc_syslib.pylib.logging as logging


class IPCP(ncp.NCP):
    __my_id = None
    __ipaddr_ok = None
    __my_ipaddr = None

    __p_dns_ok = None
    __s_dns_ok = None

    # 主DNS服务器
    __p_dns = None
    # 第二个DNS服务器
    __s_dns = None

    # 尝试此书
    __try_count = None

    def my_init(self):
        self.__my_id = 0
        self.__ipaddr_ok = False
        self.__p_dns_ok = False
        self.__s_dns_ok = False
        self.__try_count = 0

    def parse_options(self, cfg_data: bytes):
        permits = (
            2, 3, 129, 131,
        )
        results = []
        tot_size = len(cfg_data)
        if tot_size < 2: return results
        idx = 0
        while 1:
            if tot_size == idx: break
            try:
                _type = cfg_data[idx]
                length = cfg_data[idx + 1]
            except IndexError:
                results = []
                if self.debug: print("Wrong IPCP configure data")
                break
            if length < 2:
                results = []
                if self.debug: print("Wrong length field value for IPCP")
                break
            idx += 2
            e = idx + length - 2
            opt_data = cfg_data[idx:e]
            idx = e
            if len(opt_data) != length - 2:
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
                print(length, "--")
                results = []
                if self.debug: print("Wrong data length for IPCP type %d" % _type)
                return

            results.append((_type, opt_data,))

        return results

    def handle_cfg_request(self, _id: int, byte_data: bytes):
        """重写这个方法
        """
        self.send_ncp_packet(0x8021, lcp.CFG_ACK, _id, byte_data)

    def send_ncp_ipaddr_request(self):
        """发送NCP的IP地址请求
        """
        self.__try_count += 1
        self.__my_id = random.randint(1, 0xf0)
        sent_data = self.build_opt_value(3, bytes([0x00, 0x00, 0x00, 0x00]))
        self.send_ncp_packet(ncp.PPP_IPCP, lcp.CFG_REQ, self.__my_id, sent_data)

    def send_ncp_primary_dns_req(self):
        """发送主DNS请求
        """
        self.__try_count += 1
        self.__my_id = random.randint(1, 0xf0)
        sent_data = self.build_opt_value(129, bytes([0x00, 0x00, 0x00, 0x00]))
        self.send_ncp_packet(ncp.PPP_IPCP, lcp.CFG_REQ, self.__my_id, sent_data)

    def send_ncp_second_dns_req(self):
        """发送次DNS服务器请求
        """
        self.__try_count += 1
        self.__my_id = random.randint(1, 0xf0)
        sent_data = self.build_opt_value(131, bytes([0x00, 0x00, 0x00, 0x00]))
        self.send_ncp_packet(ncp.PPP_IPCP, lcp.CFG_REQ, self.__my_id, sent_data)

    def handle_cfg_ack(self, _id: int, byte_data: bytes):
        """重写这个方法
        """
        options = self.parse_options(byte_data)
        if not options: return

        if _id != self.__my_id: return

        for _type, value in options:
            if _type == 2:
                logging.print_error("PPPoE server IPCP bug,client not send configure request for type %d" % _type)
                return
            if _type == 3:
                if len(value) != 4:
                    logging.print_error("PPPoE server IPCP bug,wrong IP address length")
                    return
                self.__my_ipaddr = value
                if self.debug: print("PPPoE My IP address:%s" % socket.inet_ntop(socket.AF_INET, value))
                self.__ipaddr_ok = True
                self.pppoe.runtime.router.netif_set_ip(router.IXC_NETIF_LAN, self.__my_ipaddr, 32, False)
                break
            if _type == 129:
                if len(value) != 4:
                    logging.print_error("PPPoE server IPCP bug,wrong primary DNS address length")
                    return
                self.__p_dns = value
                if self.debug: print("PPPoE primary DNS:%s" % socket.inet_ntop(socket.AF_INET, value))
                self.__p_dns_ok = True
                break
            if _type == 131:
                if len(value) != 4:
                    logging.print_error("PPPoE server IPCP bug,wro address length")
                    return
                self.__s_dns_ok = value
                if self.debug: print("PPPoE secondary DNS:%s" % socket.inet_ntop(socket.AF_INET, value))
                self.__s_dns_ok = True
                break
            ''''''
        # 有ACK响应那么重置尝试次数
        self.__try_count = 0

    def handle_cfg_nak(self, _id: int, byte_data: bytes):
        """重写这个方法
        """
        options = self.parse_options(byte_data)
        if not options: return

        if _id != self.__my_id: return

        rejects = []
        requests = []

        for _type, value in options:
            if _type == 2:
                rejects.append(self.build_opt_value(_type, value))
                continue
            if _type in (3, 129, 131,):
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

    def start(self):
        self.send_ncp_ipaddr_request()

    def get_ipaddr(self):
        return socket.inet_ntop(socket.AF_INET, self.__my_ipaddr)

    def reset(self):
        self.my_init()

    def loop(self):
        now = time.time()
        if now - self.up_time < 1: return
        if not self.__ipaddr_ok and self.__try_count > 3:
            self.pppoe.lcp.term_req()
            return
        if not self.__ipaddr_ok:
            self.send_ncp_ipaddr_request()
            return
        if not self.__p_dns_ok and self.__try_count <= 3:
            self.send_ncp_primary_dns_req()
            return

        if not self.__s_dns_ok and self.__try_count <= 3:
            self.send_ncp_second_dns_req()
            return
        ''''''
