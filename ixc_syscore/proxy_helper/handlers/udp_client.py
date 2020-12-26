#!/usr/bin/env python3
"""UDP转发数据帧头部格式
    version:1 byte 固定为1
    is_udplite:1 byte,是否为UDPLite协议,0表示不是UDPLite数据，1表示UDPLite数据
    is_ipv6:1byte,是否为IPv6地址
    reverse:1byte 保留,默认为0
    src_port:2 bytes 源端口
    dst_port:2 bytes 目的端口
    content_length:4 bytes 数据内容长度

    数据内容:
    variable_src_ip_address  16字节或者4字节的IP地址
    variable_dst_ip_address  16字节或者4字节的IP地址
    UDP data

"""
import struct, socket
import pywind.evtframework.handlers.udp_handler as udp_handler


class client(udp_handler.udp_handler):
    def init_func(self, creator_fd, proxy_server: tuple):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.set_socket(s)
        self.connect(proxy_server)
        self.register(self.fileno)
        self.add_evt_read(self.fileno)

        return self.fileno

    def udp_readable(self, message, address):
        size = len(message)
        # 至少有20字节的头部
        if size < 20: return

        v, is_i_udplite, i_is_ipv6, r, src_port, dst_port, length = struct.unpack("!BBBBHHI", message[0:12])

        is_udplite = bool(is_i_udplite)
        is_ipv6 = bool(i_is_ipv6)

        if is_ipv6 and size < 44: return
        message = message[12:]
        if is_ipv6:
            byte_src_addr = message[0:16]
            byte_dst_addr = message[16:32]
            i = 32
        else:
            byte_src_addr = message[0:4]
            byte_dst_addr = message[4:8]
            i = 8
        udp_data = message[i:]
        self.dispatcher.proxy_helper.udp_send(byte_src_addr, byte_dst_addr, src_port, dst_port, is_udplite, is_ipv6, 8,
                                              udp_data)

    def udp_writable(self):
        self.remove_evt_write(self.fileno)

    def udp_delete(self):
        self.unregister(self.fileno)
        self.close()

    def send_to_proxy_server(self, message: bytes, src_addr: tuple, dst_addr: tuple, is_udplite=False, is_ipv6=False):
        """发送数据到代理服务器
        """
        if is_ipv6:
            content_length = 32 + len(message)
        else:
            content_length = 8 + len(message)

        if is_ipv6:
            fa = socket.AF_INET6
        else:
            fa = socket.AF_INET

        byte_src_addr = socket.inet_pton(fa, src_addr[0])
        byte_dst_addr = socket.inet_pton(fa, dst_addr[0])

        seq = [
            struct.pack("!BBBBHHI", 1, int(is_udplite), int(is_ipv6), 0, src_addr[1], dst_addr[1], content_length),
            byte_src_addr, byte_dst_addr, message
        ]

        self.send(b"".join(seq))
        self.add_evt_write(self.fileno)
