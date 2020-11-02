#!/usr/bin/env python3
"""实现DNS服务器代理,用于高级DNS过滤功能
"""
import socket, struct
import pywind.evtframework.handlers.udp_handler as udp_handler

TFTP_RRQ = 1
TFTP_WRQ = 2
TFTP_DATA = 3
TFTP_ACK = 4
TFTP_ERROR = 5

TFT_READ = 1
TFTP_WRITE = 2


class tftp(object):
    __file_dir = None
    __sessions = None
    __readable = None
    __writable = None

    def __init__(self, file_dir):
        self.__file_dir = file_dir
        self.__sessions = {}
        self.__readable = True
        self.__writable = False

    def set_file_dir(self, file_dir):
        self.__file_dir = file_dir

    def set_tftp_mode(self, mode: int):
        """设置tftp的模式,模式可以是读或者写或者可读写
        """
        if mode & TFT_READ: self.__readable = True
        if mode & TFTP_WRITE: self.__writable = True

    def handle_tftp(self, client_addr: tuple, byte_data: bytes):
        pass


class tftpd(udp_handler.udp_handler):
    __is_ipv6 = None

    def init_func(self, creator_fd, bind_ip, is_ipv6=False):
        self.__is_ipv6 = is_ipv6

        if is_ipv6:
            fa = socket.AF_INET6
        else:
            fa = socket.AF_INET

        s = socket.socket(fa, socket.SOCK_DGRAM)
        if is_ipv6: s.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
        self.set_socket(s)
        self.bind((bind_ip, 69))
        self.register(self.fileno)
        self.add_evt_read(self.fileno)

        return self.fileno

    def udp_readable(self, message, address):
        pass

    def udp_writable(self):
        self.remove_evt_write(self.fileno)

    def udp_error(self):
        pass

    def udp_delete(self):
        self.unregister(self.fileno)
        self.close()

    def udp_timeout(self):
        pass
