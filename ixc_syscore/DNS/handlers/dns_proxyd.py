#!/usr/bin/env python3
"""实现DNS服务器代理,用于实现高级DNS过滤功能
"""
import socket
import pywind.evtframework.handlers.udp_handler as udp_handler


class proxyd(udp_handler.udp_handler):
    __is_ipv6 = None

    def init_func(self, creator_fd, listen, is_ipv6=False):
        self.__is_ipv6 = is_ipv6

        if is_ipv6:
            fa = socket.AF_INET6
        else:
            fa = socket.AF_INET

        s = socket.socket(fa, socket.SOCK_DGRAM)
        if is_ipv6: s.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
        self.set_socket(s)
        self.bind(listen)
        self.register(self.fileno)
        self.add_evt_read(self.fileno)

        return self.fileno

    def udp_readable(self, message, address):
        pass

    def udp_writable(self):
        pass

    def udp_error(self):
        pass

    def udp_delete(self):
        self.unregister(self.fileno)
        self.close()
