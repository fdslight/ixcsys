#!/usr/bin/env python3
import socket, time, os

import pywind.evtframework.handlers.tcp_handler as tcp_handler
import pywind.evtframework.handlers.ssl_handler as ssl_handler


class cloud_service_client(ssl_handler.ssl_handler):
    def ssl_init(self, host: str, port: int, is_ipv6=False):
        if is_ipv6:
            fa = socket.AF_INET6
        else:
            fa = socket.AF_INET

        s = socket.socket(fa, socket.SOCK_STREAM)
        self.set_socket(s)
        self.connect((host, port))

        return self.fileno

    def connect_ok(self):
        self.register(self.fileno)
        self.add_evt_read(self.fileno)
        self.add_evt_write(self.fileno)
        # self.set_ssl_on()

    def ssl_handshake_ok(self):
        pass

    def tcp_readable(self):
        pass

    def tcp_writable(self):
        if self.writer.size() == 0: self.remove_evt_write(self.fileno)

    @property
    def device_id(self):
        return self.dispatcher.cloud_service_device_id

    @property
    def key(self):
        """通信密钥
        """
        return self.dispatcher.cloud_service_key

    def tcp_error(self):
        pass

    def tcp_timeout(self):
        pass

    def tcp_delete(self):
        pass

    def handle_rpc_request(self, fn: str, *args, **kwargs):
        """处理RPC请求
        """
        pass
