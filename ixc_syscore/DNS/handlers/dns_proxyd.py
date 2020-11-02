#!/usr/bin/env python3
"""实现DNS服务器代理,用于实现高级DNS过滤功能
"""
import socket, struct
import pywind.evtframework.handlers.udp_handler as udp_handler


class proxy_client(udp_handler.udp_handler):
    __ns1 = None
    __ns2 = None

    __is_ipv6 = None

    def init_func(self, creator_fd, ns1: str, ns2: str, is_ipv6=False):
        self.__is_ipv6 = is_ipv6
        self.__ns1 = ns1
        self.__ns2 = ns2

        if is_ipv6:
            fa = socket.AF_INET6
        else:
            fa = socket.AF_INET

        s = socket.socket(fa, socket.SOCK_DGRAM)
        if is_ipv6: s.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
        self.set_socket(s)
        if is_ipv6:
            self.bind(("::", 0))
        else:
            self.bind(("0.0.0.0", 0))

        self.register(self.fileno)
        self.add_evt_read(self.fileno)

        return self.fileno

    def udp_readable(self, message, address):
        if len(message): return

    def udp_writable(self):
        self.remove_evt_write(self.fileno)

    def udp_error(self):
        pass

    def udp_delete(self):
        self.unregister(self.fileno)
        self.close()

    def send_request_msg(self, message: bytes):
        """发送DNS请求消息
        """
        # 向两台上游nameserver发送DNS请求消息
        if self.__ns1: self.sendto(message, (self.__ns1, 53))
        if self.__ns2: self.sendto(message, (self.__ns2, 53))

        self.add_evt_write(self.fileno)


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
        if len(message) < 8: return

        dns_id = struct.unpack("!H", message[0:2])

    def udp_writable(self):
        pass

    def udp_error(self):
        pass

    def udp_delete(self):
        self.unregister(self.fileno)
        self.close()
