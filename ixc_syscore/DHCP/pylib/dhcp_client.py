#!/usr/bin/env python3

import struct, random, time, socket

import pywind.lib.netutils as netutils

import ixc_syscore.DHCP.pylib.dhcp as dhcp


class dhcp_client(object):
    __my_ipaddr = None

    __hostname = None
    __hwaddr = None
    __dhcp_server_hwaddr = None

    __dhcp_parser = None
    __dhcp_builder = None

    __runtime = None

    __dhcp_step = None

    __xid = None

    __up_time = None

    __dhcp_ok = None
    # IP地址是否检查通过
    __dhcp_ip_conflict_check_ok = None

    __lease_time = None

    __router = None
    __dnsservers = None
    __subnet_mask = None
    __broadcast_addr = None

    __dhcp_server_id = None
    __is_first = None

    __cur_step = None
    # 是否发送了续约报文
    __is_sent_renew = None

    def __init__(self, runtime, hostname: str, hwaddr: str):
        self.__runtime = runtime
        self.__hostname = hostname
        self.__hwaddr = netutils.str_hwaddr_to_bytes(hwaddr)
        self.__dhcp_parser = dhcp.dhcp_parser()
        self.__dhcp_builder = dhcp.dhcp_builder()
        self.__dnsservers = []

        self.reset()

    def reset(self):
        self.__dhcp_step = 0
        self.__dhcp_parser.reset()
        self.__dhcp_builder.reset()
        self.__up_time = time.time()
        self.__dhcp_ok = False
        self.__is_first = True
        self.__dhcp_ip_conflict_check_ok = False
        self.__cur_step = 1
        self.__is_sent_renew = False

    def handle_dhcp_response(self, response_data: bytes):
        try:
            dst_hwaddr, src_hwaddr, dst_addr, src_addr, options, is_server = self.__dhcp_parser.parse_from_link_data(
                response_data)
        except:
            return

        if is_server: return

        x = self.get_dhcp_opt_value(options, 53)
        msg_type = x[0]
        if not msg_type: return

        self.__dhcp_server_hwaddr = src_hwaddr

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

        subnet_mask = self.get_dhcp_opt_value(options, 1)
        if not subnet_mask: return
        if len(subnet_mask) != 4: return

        # 一些DHCP Server可能不提供广播地址
        broadcast_addr = self.get_dhcp_opt_value(options, 28)
        if broadcast_addr:
            if len(broadcast_addr) != 4: return

        dnsserver = self.get_dhcp_opt_value(options, 6)

        if dnsserver:
            # 域名服务器必须是4的倍数
            if len(dnsserver) % 4 != 0: return
            while 1:
                if not dnsserver: break
                str_addr = socket.inet_ntop(socket.AF_INET, dnsserver[0:4])
                self.__dnsservers.append(str_addr)
                dnsserver = dnsserver[4:]

        router = self.get_dhcp_opt_value(options, 3)
        if router:
            if len(router) != 4: return

        self.__cur_step = 4
        self.__my_ipaddr = self.__dhcp_parser.yiaddr
        self.__dhcp_ok = True
        self.__up_time = time.time()

        self.__router = router
        self.__lease_time, = struct.unpack("!I", ipaddr_lease_time)
        self.__subnet_mask = subnet_mask
        self.__broadcast_addr = broadcast_addr
        self.__is_sent_renew = False

    def handle_dhcp_nak(self, options: list):
        t = time.time()

    def handle_dhcp_offer(self, options: list):
        dhcp_server_id = self.get_dhcp_opt_value(options, 54)
        if not dhcp_server_id: return

        self.__up_time = time.time()
        self.__cur_step = 3
        self.__dhcp_server_id = dhcp_server_id
        self.__my_ipaddr = self.__dhcp_parser.yiaddr

        self.__dhcp_builder.reset()
        self.__dhcp_builder.ciaddr = self.__hwaddr
        self.__dhcp_builder.xid = self.__xid

        new_opts = [
            (53, struct.pack("!B", 3)),
            (54, dhcp_server_id),
            (12, self.__hostname.encode()),
            (61, struct.pack("!B6s", 0x01, self.__hwaddr)),
            (50, self.__dhcp_parser.yiaddr),
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
        # 此处发送ARP数据包进行验证IP地址是否重复
        self.__runtime.send_arp_request(self.__hwaddr, self.__my_ipaddr, is_server=False)

    def send_dhcp_discover(self):
        self.__cur_step = 1
        self.__up_time = time.time()
        self.__dhcp_parser.xid = random.randint(1, 0xfffffffe)
        self.__xid = self.__dhcp_parser.xid
        self.__dhcp_ip_conflict_check_ok = False

        options = [
            # DHCP msg type
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

    def send_dhcp_request(self, dst_hwaddr=bytes([0xff, 0xff, 0xff, 0xff, 0xff, 0xff])):
        """发送DHCP请求报文
        :return:
        """
        self.__dhcp_builder.reset()
        self.__dhcp_builder.ciaddr = self.__hwaddr
        self.__dhcp_builder.xid = self.__xid
        # 注意这里的时间要更新，避免连续发送dhcp request数据包
        self.__up_time = time.time()

        options = [
            (53, struct.pack("!B", 3)),
            (54, self.__dhcp_server_id),
            (12, self.__hostname.encode()),
            (61, self.__hwaddr,),
            (50, self.__dhcp_parser.yiaddr),
            (55, struct.pack("BBBBBB", 3, 1, 3, 6, 28, 50))
        ]

        link_data = self.__dhcp_builder.build_to_link_data(
            dst_hwaddr,
            self.__hwaddr,
            bytes([0xff, 0xff, 0xff, 0xff]),
            bytes(4),
            options,
            is_server=False
        )
        self.__runtime.send_dhcp_client_msg(link_data)

    def send_dhcp_decline(self):
        """广播发送DHCP decline报文,告知地址已经被使用
        :return:
        """
        if self.__dhcp_step not in (3, 4,): return

        self.__dhcp_builder.reset()
        self.__dhcp_builder.ciaddr = self.__hwaddr
        self.__dhcp_builder.xid = self.__xid

        new_opts = [
            (53, struct.pack("!B", 4)),
            (54, self.__dhcp_server_id),
            (12, self.__hostname.encode()),
            (61, self.__hwaddr,),
            (50, self.__dhcp_parser.yiaddr),
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

    def loop(self):
        """自动执行
        """
        t = time.time()
        v = t - self.__up_time

        # 如果DHCP分配成功,并且超时都没有收到重复ARP数据包,那么该IP地址不存在
        if self.__dhcp_ok and not self.__dhcp_ip_conflict_check_ok:
            if v > 10:
                s_ip = socket.inet_ntop(socket.AF_INET, self.__my_ipaddr)
                s_mask = socket.inet_ntop(socket.AF_INET, self.__subnet_mask)
                prefix = netutils.mask_to_prefix(s_mask, is_ipv6=False)

                ok = self.__runtime.set_wan_ip(s_ip, prefix, is_ipv6=False)

                if self.__runtime.debug:
                    print("IP address:", s_ip, s_mask)
                if self.__router:
                    s_gw = socket.inet_ntop(socket.AF_INET, self.__router)
                    if self.__runtime.debug: print("gateway:", s_gw)
                    ok = self.__runtime.set_default_route(s_gw, is_ipv6=False)
                if self.__dnsservers:
                    s_ns1 = self.__dnsservers[0]
                    if self.__runtime.debug: print("nameserver1:", s_ns1)
                    if len(self.__dnsservers) > 1:
                        s_ns2 = self.__dnsservers[1]
                        if self.__runtime.debug: print("nameserver2:", s_ns2)
                    else:
                        s_ns2 = None
                    self.__runtime.set_nameservers(s_ns1, s_ns2, is_ipv6=False)

                self.__dhcp_ip_conflict_check_ok = True
            else:
                return

        if self.dhcp_ok:
            self.dhcp_keep_handle()
            return

        if self.__is_first:
            self.send_dhcp_discover()
            self.__is_first = False
            return

        if v > 10 and not self.__dhcp_ok:
            self.send_dhcp_discover()
            return

    def ip_addr_get(self):
        return socket.inet_ntoa(self.__my_ipaddr)

    def subnet_mask_get(self):
        return socket.inet_ntoa(self.__subnet_mask)

    def broadcast_addr_get(self):
        return socket.inet_ntoa(self.__broadcast_addr)

    def router_addr_get(self):
        return socket.inet_ntoa(self.__router)

    def dnsservers_addr_get(self):
        return self.__dnsservers

    @property
    def dhcp_ok(self):
        return self.__dhcp_ok and self.__dhcp_ip_conflict_check_ok

    @property
    def my_hwaddr(self):
        return self.__hwaddr

    def handle_dhcp_msg(self, msg: bytes):
        self.handle_dhcp_response(msg)

    def handle_arp(self, dst_hwaddr: bytes, src_hwaddr: bytes, arp_info):
        # 只允许广播和发送到本机器的ARP数据包
        brd = bytes([0xff, 0xff, 0xff, 0xff, 0xff, 0xff])
        if dst_hwaddr != brd or dst_hwaddr != self.__hwaddr: return
        op, _dst_hwaddr, _src_hwaddr, src_ipaddr, dst_ipaddr = arp_info

        if _dst_hwaddr != self.__hwaddr: return
        # IP地址如果不冲突那么直接返回
        if src_ipaddr != self.__my_ipaddr: return

        #  此处处理DHCP分配到的IP地址与局域网其他机器冲突的情况
        self.__dhcp_ip_conflict_check_ok = False
        self.__dhcp_ok = False

        self.send_dhcp_decline()

    def dhcp_keep_handle(self):
        """保持DHCP地址
        :return:
        """
        t = time.time()
        v = t - self.__up_time

        # 如果发送了renew并且未回复那么重置
        if self.__is_sent_renew and v > 30:
            self.reset()
            return

            # 如果开启积极心跳,那么就60s续约一次
        if self.__runtime.positive_dhcp_client_request:
            timeout = 60
        else:
            timeout = int(self.__lease_time / 2)

        # 此处执行续约操作
        if v > timeout:
            self.__is_sent_renew = True
            if self.__runtime.debug: print("renew request send")
            self.send_dhcp_request(dst_hwaddr=bytes(self.__dhcp_server_hwaddr))
