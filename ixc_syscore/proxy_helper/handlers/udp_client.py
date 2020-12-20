#!/usr/bin/env python3

import pywind.evtframework.handlers.udp_handler as udp_handler


class client(udp_handler.udp_handler):
    def init_func(self, creator_fd, proxy_server: tuple):
        pass

    def udp_readable(self, message, address):
        pass

    def udp_writable(self):
        pass

    def send_to_proxy_server(self, message: bytes, src_addr: tuple, dst_addr: tuple, is_ipv6=False):
        """发送数据到代理服务器
        """
        pass
