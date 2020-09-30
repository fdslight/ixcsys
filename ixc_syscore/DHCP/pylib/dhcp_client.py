#!/usr/bin/env python3
import struct, random, time, socket
import pywind.lib.netutils as netutils
import ixc_syscore.DHCP.pylib.dhcp as dhcp


class dhcp_client(object):
    __my_ipaddr = None

    __hostname = None
    __hwaddr = None

    __dhcp_parser = None
    __dhcp_builder = None

    __runtime = None

    __dhcp_step = None

    __xid = None

    __up_time = None

    __dhcp_ok = None

    __rebind_time = None
    __renewal_time = None
    __lease_time = None

    __router = None
    __dnsserver = None

    __tmp_dst_hwaddr = None
    __tmp_src_hwaddr = None
    __tmp_dst_addr = None
    __tmp_src_addr = None
    __dhcp_server_id = None

    def __init__(self, runtime, hostname: str, hwaddr: str):
        self.__runtime = runtime
        self.__hostname = hostname
        self.__hwaddr = netutils.ifaddr_to_bytes(hwaddr)
        self.__dhcp_step = 0

        self.__dhcp_parser = dhcp.dhcp_parser()
        self.__dhcp_builder = dhcp.dhcp_builder()
        self.__up_time = time.time()
        self.__dhcp_ok = False

    def handle_dhcp_response(self, response_data: bytes):
        try:
            dst_hwaddr, src_hwaddr, dst_addr, src_addr, options, is_server = self.__dhcp_parser.parse_from_link_data(
                response_data)
        except:
            return

        if is_server: return

        self.__tmp_dst_hwaddr = dst_hwaddr
        self.__tmp_src_hwaddr = src_hwaddr
        self.__tmp_dst_addr = dst_addr
        self.__tmp_src_addr = src_addr

        x = self.get_dhcp_opt_value(options, 53)
        msg_type = x[0]
        if not msg_type: return

        if 2 == msg_type:
            self.handle_dhcp_offer(options)
        if 5 == msg_type:
            self.handle_dhcp_ack(options)

    def handle_dhcp_ack(self, options: list):
        dhcp_server_id = self.get_dhcp_opt_value(options, 54)
        if not dhcp_server_id: return

        if dhcp_server_id != self.__dhcp_server_id: return

        ipaddr_lease_time = self.get_dhcp_opt_value(options, 51)
        if not ipaddr_lease_time: return
        if len(ipaddr_lease_time) != 4: return

        renewal_time = self.get_dhcp_opt_value(options, 58)
        if not renewal_time: return
        if len(renewal_time) != 4: return

        rebinding_time = self.get_dhcp_opt_value(options, 59)
        if not renewal_time: return
        if len(rebinding_time) != 4: return

        subnet_mask = self.get_dhcp_opt_value(options, 1)
        if not subnet_mask: return
        if len(subnet_mask) != 4: return

        broadcast_addr = self.get_dhcp_opt_value(options, 28)
        if not broadcast_addr: return
        if len(broadcast_addr) != 4: return

        dnsserver = self.get_dhcp_opt_value(options, 6)
        if dnsserver and len(dnsserver) != 4: return
        if dnsserver:
            self.__dnsserver = dnsserver

        router = self.get_dhcp_opt_value(options, 3)
        if router and len(router) != 4: return

        self.__router = router
        self.__my_ipaddr = self.__dhcp_parser.yiaddr



    def handle_dhcp_nak(self, options: list):
        pass

    def handle_dhcp_offer(self, options: list):
        dhcp_server_id = self.get_dhcp_opt_value(options, 54)
        if not dhcp_server_id: return

        ipaddr_lease_time = self.get_dhcp_opt_value(options, 51)
        if not ipaddr_lease_time: return
        if len(ipaddr_lease_time) != 4: return

        self.__dhcp_server_id = dhcp_server_id

        self.__dhcp_builder.reset()
        self.__dhcp_builder.ciaddr = self.__hwaddr
        self.__dhcp_builder.xid = self.__xid

        self.__my_ipaddr = self.__dhcp_parser.yiaddr

        new_opts = [
            (53, struct.pack("!B", 3)),
            (54, dhcp_server_id),
            (12, self.__hostname.encode()),
            (61, self.__hwaddr,),
            (50, self.__dhcp_parser.yiaddr),
            (51, ipaddr_lease_time,),
            (55, struct.pack("BBBBBB", 3, 1, 3, 6, 28, 50))
        ]

        byte_data = self.__dhcp_builder.build_to_link_data(
            bytes([0xff, 0xff, 0xff, 0xff, 0xff, 0xff]),
            self.__hwaddr,
            bytes([0xff, 0xff, 0xff, 0xff]),
            bytes(4),
            new_opts,
            is_server=False
        )
        self.__runtime.send_dhcp_client_msg(byte_data)

    def send_dhcp_discover(self):
        self.__dhcp_parser.xid = random.randint(1, 0xfffffffe)
        self.__xid = self.__dhcp_parser.xid

        options = [
            # dhcp msg type
            (53, struct.pack("b", 1)),
            # client id
            (61, self.__hwaddr,),
            (12, self.__hostname.encode()),
            # parameter request list
            (55, struct.pack("BBBBBB", 3, 1, 3, 6, 28, 50))
        ]

        link_data = self.__dhcp_builder.build_to_link_data(
            bytes([0xff, 0xff, 0xff, 0xff, 0xff, 0xff]),
            self.__hwaddr,
            bytes([0xff, 0xff, 0xff, 0xff]),
            bytes(4),
            options,
            is_server=False
        )
        self.__runtime.send_dhcp_client_msg(link_data)

    def get_dhcp_opt_value(self, options: list, code: int):
        rs = None
        for name, length, value in options:
            if name == code:
                rs = value
                break
            ''''''
        return rs

    def send_dhcp_request(self):
        """发送DHCP请求报文
        :return:
        """
        pass

    def send_dhcp_release(self):
        """发送DHCP release报文
        :return:
        """
        pass

    def send_dhcp_decline(self):
        """发送DHCP decline报文
        :return:
        """
        pass

    def do(self):
        """自动执行
        """
        if self.dhcp_ok:
            self.dhcp_keep_handle()
            return

        if 0 == self.__dhcp_step:
            self.__dhcp_step = 1
            self.send_dhcp_discover()

    @property
    def dhcp_ok(self):
        return self.__dhcp_ok

    def handle(self, msg: bytes):
        self.handle_dhcp_response(msg)

    def dhcp_keep_handle(self):
        """保持DHCP地址
        :return:
        """
        pass
