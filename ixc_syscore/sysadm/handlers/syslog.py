#!/usr/bin/env python3
"""日志接收
"""
import socket
import pywind.evtframework.handlers.udp_handler as udp_handler


class syslogd(udp_handler.udp_handler):
    def init_func(self, creator_fd):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.set_socket(s)
        self.bind(("127.0.0.1", 514))
        self.register(self.fileno)

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
