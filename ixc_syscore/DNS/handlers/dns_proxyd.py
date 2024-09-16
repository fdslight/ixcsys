#!/usr/bin/env python3
"""实现DNS服务器代理,用于实现高级DNS过滤功能
"""
import socket
import pywind.evtframework.handlers.udp_handler as udp_handler


class proxy_client(udp_handler.udp_handler):
    __ns1 = None
    __ns2 = None

    __is_ipv6 = None
    __forward_port = None

    def init_func(self, creator_fd, ns1: str, ns2: str, is_ipv6=False):
        self.__is_ipv6 = is_ipv6

        # 避免类型错误报错
        if not ns1: ns1 = ""
        if not ns2: ns2 = ""

        self.__ns1 = ns1
        self.__ns2 = ns2
        self.__forward_port = -1

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
        if len(message) < 8: return
        # 检查地址是否是DNS服务器的地址
        if address[0] not in (self.__ns1, self.__ns2, "127.0.0.1",): return
        # 核对是否是允许的对端端口
        if address[1] not in (53, self.__forward_port, self.dispatcher.sec_dns_forward_port,): return
        # 只允许非53的loopback端口
        if address[1] != 53 and address[0] != "127.0.0.1": return

        self.dispatcher.handle_msg_from_dnsserver(message)

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

    def send_forward_msg(self, message: bytes):
        """only support IPv4 address
        """
        if self.__forward_port < 1: return
        self.sendto(message, ("127.0.0.1", self.__forward_port))
        self.add_evt_write(self.fileno)

    def send_forward_msg2(self, message: bytes, port: int):
        """
        Only support IPv4 address
        """
        self.sendto(message, ("127.0.0.1", port))
        self.add_evt_write(self.fileno)

    def set_forward_port(self, port: int):
        self.__forward_port = port

    def get_port(self):
        return self.socket.getsockname()[1]

    def get_nameservers(self):
        return [self.__ns1, self.__ns2]

    def set_nameservers(self, ns1: str, ns2: str):
        if not ns1: ns1 = ""
        if not ns2: ns2 = ""

        self.__ns1 = ns1
        self.__ns2 = ns2


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
        # 这里可能存在绑定失败的情况
        try:
            self.bind(listen)
        except OSError:
            self.close()
            return -1
        self.register(self.fileno)
        self.add_evt_read(self.fileno)

        return self.fileno

    def udp_readable(self, message, address):
        if len(message) < 16: return
        self.dispatcher.handle_msg_from_dnsclient(self.fileno, message, address, is_ipv6=self.__is_ipv6)

    def udp_writable(self):
        self.remove_evt_write(self.fileno)

    def udp_error(self):
        pass

    def udp_delete(self):
        self.unregister(self.fileno)
        self.close()

    def send_msg(self, message: bytes, client_addr: tuple):
        self.sendto(message, client_addr)
        self.add_evt_write(self.fileno)
