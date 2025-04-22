#!/usr/bin/env python3
# 实现dhcpv6客户端stateless

import time, struct, socket, random
import ixc_syscore.DHCP.pylib.netpkt as netpkt
import ixc_syslib.pylib.logging as logging
import pywind.lib.netutils as netutils
import ixc_syslib.pylib.RPCClient as RPC


class dhcpv6c(object):
    __runtime = None
    __duid_ll = None
    __xid = None

    __hosname = None
    __wan_hwaddr = None

    __up_time = None

    __nameservers = None

    def __init__(self, runtime, hostname, wan_hwaddr):
        self.__runtime = runtime
        self.__hostname = hostname
        self.__wan_hwaddr = wan_hwaddr
        self.__up_time = time.time()
        self.__duid_ll = netutils.str_hwaddr_to_bytes(wan_hwaddr)
        self.__nameservers = []

    def get_my_local_address(self, mac_address):
        binary_mac = bin(int(mac_address[:2], 16))[2:].zfill(8)
        flipped_mac = binary_mac[:7] + "1" + binary_mac[8:]
        flipped_mac_hex = hex(int(flipped_mac, 2))[2:].zfill(2)
        eui64 = flipped_mac_hex + mac_address[2:6] + "FF:FE:" + mac_address[6:]
        byte_eui64 = netutils.str_hwaddr_to_bytes(eui64)
        byte_local_link = socket.inet_pton(socket.AF_INET6, "fe80::")

        _list = list(byte_local_link)
        b = 8
        for n in byte_eui64:
            _list[b] = n
            b += 1
        z = bytes(_list)

        return socket.inet_ntop(socket.AF_INET6, z)

    def send_ip_data(self, dst_ip6: str, src_ip6: str, data: bytes):
        src_ip6_byte = socket.inet_pton(socket.AF_INET6, src_ip6)
        dst_ip6_byte = socket.inet_pton(socket.AF_INET6, dst_ip6)

        payload_length = len(data)

        label = random.randint(1, 0xffffe)
        v = (6 << 28) | label
        ip6_header = [
            struct.pack("!I", v),
            struct.pack("!H", payload_length),
            bytes([17, 64]),
            src_ip6_byte, dst_ip6_byte
        ]

        header = b"".join(ip6_header)
        # 填充空的14字节以太网头部,因为运行在pppoe上,不需要以太网头部
        new_data = bytes(14) + header + data
        self.__runtime.send_dhcp_client_msg(new_data)

    def send_udp_data(self, dst_ip6: str, src_ip6: str, dst_port: int, src_port: int, data: bytes):
        src_ip6_byte = socket.inet_pton(socket.AF_INET6, src_ip6)
        dst_ip6_byte = socket.inet_pton(socket.AF_INET6, dst_ip6)

        udppkt = netpkt.build_udppkt(src_ip6_byte, dst_ip6_byte, src_port, dst_port, data, is_ipv6=True)
        self.send_ip_data(dst_ip6, src_ip6, udppkt)

    def build_option(self, code, data: bytes):
        length = len(data)

        return struct.pack("!HH", code, length) + data

    def send_dhcp_request(self):
        self.__xid = random.randint(1, 0xfffffe)
        # print(hex(self.__xid))

        x1 = (self.__xid & 0xff0000) >> 16
        x2 = (self.__xid & 0x00ff00) >> 8
        x3 = self.__xid & 0x0000ff

        seq = [
            # information request
            bytes([11, x1, x2, x3]),
            # elapsed time
            self.build_option(8, bytes(2)),
            # duid
            self.build_option(1, struct.pack("!HHI6s", 1, 1, int(time.time()), self.__duid_ll)),
            # vendor
            self.build_option(16, struct.pack("!I", 311) + self.__hostname.encode()),
            # option request
            self.build_option(6, struct.pack("!HHHH", 17, 23, 24, 32)),
        ]

        dhcp_data = b"".join(seq)

        self.send_udp_data("FF02::1:2", self.get_my_local_address(self.__wan_hwaddr), 547, 546, dhcp_data)

    def handle_dhcp_msg(self, ip_data: bytes):
        dhcp_data = ip_data[48:]
        if len(dhcp_data) < 4: return

        msg_type = dhcp_data[0]
        xid = (dhcp_data[1] << 16) | (dhcp_data[2] << 8) | dhcp_data[3]

        if msg_type != 7: return
        if xid != self.__xid: return

        # print(xid, self.__xid)
        # parse options
        dhcp_data = dhcp_data[4:]
        is_err = False

        opts = {}

        while 1:
            if len(dhcp_data) == 0: break
            if len(dhcp_data) < 4:
                is_err = True
                break
            _type, length = struct.unpack("!HH", dhcp_data[0:4])
            dhcp_data = dhcp_data[4:]
            value = dhcp_data[0:length]
            if len(value) != length:
                is_err = True
                break
            opts[_type] = value
            dhcp_data = dhcp_data[length:]

        # print(opts)
        if is_err:
            logging.print_alert("dhcpv6 server response error")
            return

        if 13 not in opts:
            logging.print_alert("dhcpv6 server not response status code")
            return

        if 23 not in opts:
            logging.print_alert("dhcpv6 server not response dns server")
            return

        value = opts[23]
        if len(value) % 16 != 0:
            logging.print_alert("dhcpv6 server response wrong dns server format")
            return

        nameservers = []
        b = 0
        e = 16
        while 1:
            nameserver = value[b:e]
            if not nameserver: break
            nameservers.append(socket.inet_ntop(socket.AF_INET6, nameserver))
            b = e
            e += 16

        if len(nameservers) < 1: return
        # 如果少于2台服务器,添加一个空的
        if len(nameservers) == 1:
            nameservers.append("")
        # print(opts)
        self.__nameservers = []
        logging.print_alert("dhcpv6 get ipv6 nameservers %s" % " ".join(nameservers))
        self.set_system_dnsserver()

    def set_system_dnsserver(self):
        nameservers = self.__nameservers
        RPC.fn_call("DNS", "/config", "set_ip6_nameservers_from_dhcpv6", nameservers[0], nameservers[1])

    def loop(self):
        now = time.time()
        # 如果已经获取到DNS服务器,那么1小时获取一次,否则60秒查找一次
        if self.__nameservers:
            timeout = 3600
        else:
            timeout = 60
        if now - self.__up_time < timeout:
            return
        self.__up_time = now
        self.send_dhcp_request()
