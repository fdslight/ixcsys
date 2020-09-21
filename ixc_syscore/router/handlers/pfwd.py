#!/usr/bin/env python3
"""数据包重定向
"""
import socket, struct
import pywind.evtframework.handlers.udp_handler as udp_handler

HEADER_FMT = "!16sHbb"


class pfwd(udp_handler.udp_handler):
    __sock_info = None

    # 链路层重定向表
    __link_fwd_tb = None
    # IP层重定向表
    __ip_fwd_tb = None

    __pkt_size = None

    def init_func(self, creator_fd):
        self.__link_fwd_tb = {}
        self.__ip_fwd_tb = {}

        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.set_socket(s)
        self.bind(("127.0.0.1", 0))
        self.__sock_info = s.getsockname()

        self.register(self.fileno)
        self.add_evt_read(self.fileno)

        return self.fileno

    def udp_readable(self, message, address):
        """
        :param message:
        :param address:
        :return:
        """
        # 限制只能本机器进行通讯
        if address[0] != "127.0.0.1": return
        self.__pkt_size = len(message)
        if self.__pkt_size < 40: return

    def udp_writable(self):
        pass

    def udp_error(self):
        self.delete_handler(self.fileno)

    def udp_delete(self):
        self.unregister(self.fileno)
        self.close()

    def handle_link_from_netstack(self, link_proto: int, ipproto: int, flags: int, msg: bytes):
        pass

    def handle_ip_from_netstack(self, link_proto: int, ipproto: int, flags: int, msg: bytes):
        pass

    def recv_from_netstack(self, link_proto: int, ipproto: int, flags: int, msg: bytes):
        """从协议栈接收数据
        :param link_proto:
        :param ipproto:
        :param flags:
        :param msg:
        :return:
        """
        if link_proto:
            self.handle_link_from_netstack(link_proto, ipproto, flags, msg)
        else:
            self.handle_ip_from_netstack(link_proto, ipproto, flags, msg)
