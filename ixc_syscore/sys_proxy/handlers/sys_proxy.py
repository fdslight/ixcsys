#!/usr/bin/env python3
"""实现系统代理
"""
import socket, struct, os, time
import pywind.evtframework.handlers.tcp_handler as tcp_handler

import ixc_syslib.pylib.logging as logging

class listener(tcp_handler.tcp_handler):
    __is_ipv6 = None

    def init_func(self, creator_fd, bind_ip, is_ipv6=False):
        self.__is_ipv6 = is_ipv6

        if is_ipv6:
            fa = socket.AF_INET6
        else:
            fa = socket.AF_INET

        s = socket.socket(fa, socket.SOCK_STREAM)
        if is_ipv6: s.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
        self.set_socket(s)
        self.bind((bind_ip, 69))
        self.register(self.fileno)
        self.add_evt_read(self.fileno)

        return self.fileno

    def tcp_readable(self):
        pass

    def tcp_writable(self):
        if self.writer.size() == 0: self.remove_evt_write(self.fileno)

    def tcp_timeout(self):
        pass

    def tcp_delete(self):
        self.unregister(self.fileno)
        self.close()
