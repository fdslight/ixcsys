#!/usr/bin/env python3

import socket, pickle
import pywind.evtframework.handlers.udp_handler as udp_handler


class dns_proxy(udp_handler.udp_handler):
    __forward_port = None

    def init_func(self, creator_fd):
        self.__forward_port = -1
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        self.set_socket(s)
        self.bind(("127.0.0.1", 0))
        self.register(self.fileno)
        self.add_evt_read(self.fileno)
        self.set_timeout(self.fileno, 10)

        return self.fileno

    def udp_readable(self, message, address):
        if address[0] != "127.0.0.1" and address[0] != self.dispatcher.manage_addr: return
        if address[1] != self.__forward_port: return

        o = pickle.loads(message)
        dns_msg = o["message"]
        action = o["action"]

        self.dispatcher.send_dns_request_to_tunnel(action, dns_msg)

    def udp_writable(self):
        self.remove_evt_write(self.fileno)

    def get_port(self):
        return self.getsockname()[1]

    def send_dns_msg(self, message: bytes):
        self.add_evt_write(self.fileno)
        self.sendto(message, (self.dispatcher.manage_addr, self.__forward_port))

    def set_forward(self, port: int):
        self.__forward_port = port

    def udp_timeout(self):
        pass
