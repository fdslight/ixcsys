#!/usr/bin/env python3
# 连接监控,用于检查网络是否中断
import socket
import pywind.evtframework.handlers.tcp_handler as tcp_handler


class conn_mon_client(tcp_handler.tcp_handler):
    __is_ipv6 = None

    def init_func(self, creator_fd, host, port, is_ipv6=False):
        self.__is_ipv6 = is_ipv6

        if is_ipv6:
            fa = socket.AF_INET6
        else:
            fa = socket.AF_INET

        s = socket.socket(fa, socket.SOCK_STREAM)
        self.set_socket(s)
        self.register(self.fileno)

        return self.connect((host, port))

    def connect_ok(self):
        self.dispatcher.report_network_status(True)

    def tcp_timeout(self):
        if not self.is_conn_ok():
            self.dispatcher.report_network_status(False)
            return
        self.delete_handler(self.fileno)

    def tcp_error(self):
        self.delete_handler(self.fileno)

    def tcp_delete(self):
        self.unregister(self.fileno)
        self.close()
