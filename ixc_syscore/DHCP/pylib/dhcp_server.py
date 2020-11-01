#!/usr/bin/env python3
import socket, struct

import pywind.lib.netutils as netutils

import ixc_syscore.DHCP.pylib.dhcp as dhcp
import ixc_syscore.DHCP.pylib.ipalloc as ipalloc

import ixc_syslib.pylib.logging as logging


class dhcp_server(object):
    __my_ipaddr = None

    __hostname = None
    __hwaddr = None

    __dhcp_parser = None
    __dhcp_builder = None

    __runtime = None
    __client_hwaddr = None

    __alloc = None

    __TIMEOUT = 1800

    __mask_bytes = None
    __route_bytes = None
    __dns_bytes = None

    def __init__(self, runtime, my_ipaddr: str, hostname: str, hwaddr: str, addr_begin: str, addr_finish: str,
                 subnet: str, prefix: int):
        self.__runtime = runtime
        self.__mask_bytes = socket.inet_pton(socket.AF_INET, netutils.ip_prefix_convert(prefix))
        self.__route_bytes = socket.inet_pton(socket.AF_INET, my_ipaddr)
        self.__dns_bytes = socket.inet_pton(socket.AF_INET, self.__runtime.manage_addr)

        self.__alloc = ipalloc.alloc(addr_begin, addr_finish, subnet, int(prefix))
        self.__my_ipaddr = socket.inet_pton(socket.AF_INET, my_ipaddr)
        self.__hostname = hostname.encode()
        self.__hwaddr = netutils.str_hwaddr_to_bytes(hwaddr)

        self.__dhcp_parser = dhcp.dhcp_parser()
        self.__dhcp_builder = dhcp.dhcp_builder()

    def get_dhcp_opt_value(self, options: list, code: int):
        rs = None
        for name, length, value in options:
            if name == code:
                rs = value
                break
            ''''''
        return rs

    def build_dhcp_response(self, msg_type: int, opts: list):
        brd_ifaddr = bytes([0xff, 0xff, 0xff, 0xff, 0xff, 0xff])

        self.__dhcp_builder.op = 2
        self.__dhcp_builder.xid = self.__dhcp_parser.xid
        self.__dhcp_builder.secs = self.__dhcp_parser.secs
        self.__dhcp_builder.flags = self.__dhcp_parser.flags

        s_hwaddr = netutils.byte_hwaddr_to_str(self.__client_hwaddr)
        s_yiaddr = self.__alloc.get_ipaddr(s_hwaddr)
        if not s_yiaddr: return

        self.__dhcp_builder.chaddr = self.__client_hwaddr
        self.__dhcp_builder.ciaddr = socket.inet_pton(socket.AF_INET, s_yiaddr)

        src_hwaddr = self.__hwaddr
        if self.__dhcp_parser.flags:
            dst_hwaddr = brd_ifaddr
        else:
            dst_hwaddr = self.__client_hwaddr

        opts.insert(0, (53, struct.pack("B", msg_type)))
        opts.append((54, self.__my_ipaddr))

        link_data = self.__dhcp_builder.build_to_link_data(
            dst_hwaddr, src_hwaddr, bytes([0xff, 0xff, 0xff, 0xff]), self.__my_ipaddr,
            options=opts, is_server=True
        )
        self.__runtime.send_dhcp_server_msg(link_data)

    def handle_dhcp_discover_req(self, opts: list):
        self.__dhcp_builder.reset()

        request_list = self.get_dhcp_opt_value(opts, 55)
        if not request_list: return
        resp_opts = []
        ipaddr = self.__alloc.get_ipaddr(self.__client_hwaddr)

        if not ipaddr: return

        your_byte_ipaddr = socket.inet_pton(socket.AF_INET, ipaddr)

        resp_opts.append((53, bytes([2])))

        for code in request_list:
            if code == 1:
                resp_opts.append((code, self.__mask_bytes,))
            if code == 6 and self.__dns_bytes:
                resp_opts.append((code, self.__dns_bytes))
            if code == 54:
                resp_opts.append((code, self.__my_ipaddr))

        flags = self.__dhcp_parser.flags & 0x8000
        if flags > 0:
            dst_hwaddr = self.__client_hwaddr
        else:
            dst_hwaddr = bytes([0xff, 0xff, 0xff, 0xff, 0xff, 0xff])

        self.__dhcp_builder.xid = self.__dhcp_parser.xid
        self.__dhcp_builder.op = 2
        self.__dhcp_builder.yiaddr = your_byte_ipaddr
        self.__dhcp_builder.siaddr = self.__my_ipaddr
        self.__dhcp_builder.chaddr = self.__client_hwaddr

        resp_data = self.__dhcp_builder.build_to_link_data(
            dst_hwaddr, self.__hwaddr, bytes([0xff, 0xff, 0xff, 0xff]), self.__my_ipaddr, resp_opts, is_server=True
        )
        self.__runtime.send_dhcp_server_msg(resp_data)

    def handle_dhcp_request(self, opts: list):
        client_id = self.get_dhcp_opt_value(opts, 61)
        request_ip = self.get_dhcp_opt_value(opts, 50)
        server_id = self.get_dhcp_opt_value(opts, 54)
        request_list = self.get_dhcp_opt_value(opts, 55)

        if not request_ip: return

    def handle_dhcp_decline(self, opts: list):
        pass

    def handle_dhcp_release(self, opts: list):
        pass

    def handle_dhcp_msg(self, msg: bytes):
        try:
            dst_hwaddr, src_hwaddr, dst_addr, src_addr, options, is_server = self.__dhcp_parser.parse_from_link_data(
                msg)
        except:
            return

        self.__client_hwaddr = src_hwaddr
        if not is_server: return
        x = self.get_dhcp_opt_value(options, 53)
        msg_type = x[0]
        if not msg_type: return

        if msg_type not in (1, 3, 4, 7,): return

        if msg_type == 1:
            self.handle_dhcp_discover_req(options)
            return

        if msg_type == 3:
            self.handle_dhcp_request(options)
            return

        if msg_type == 4:
            self.handle_dhcp_decline(options)
            return

        self.handle_dhcp_release(options)

    def handle_arp(self, dst_hwaddr: bytes, src_hwaddr: bytes, arp_info):
        # 只允许广播和发送到本机器的ARP数据包
        brd = bytes([0xff, 0xff, 0xff, 0xff, 0xff, 0xff])
        if dst_hwaddr != brd or dst_hwaddr != self.__hwaddr: return

        op, _dst_hwaddr, _src_hwaddr, src_ipaddr, dst_ipaddr = arp_info
        if _dst_hwaddr != self.__hwaddr: return

    def set_timeout(self, timeout: int):
        """设置DHCP IP超时时间
        """
        self.__TIMEOUT = timeout

    def loop(self):
        self.__alloc.recycle()
