#!/usr/bin/env python3

import socket, struct
import pywind.evtframework.handlers.udp_handler as udp_handler


class proc_message(udp_handler.udp_handler):
    __key = None
    __port = None

    def init_func(self, creator_fd, key: bytes):
        """
        :param key:4 bytes key
        """
        self.__port = -1
        self.__key = key
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.set_socket(s)
        self.bind(("127.0.0.1", 0))
        self.register(self.fileno)
        self.add_evt_read(self.fileno)

        return self.fileno

    def handle_cmd_msg(self, message: bytes):
        self.__port, = struct.unpack("!H", message[0:2])

    def udp_readable(self, message, address):
        if address[1] != self.__port: return
        if len(message) < 7: return
        if message[0:4] != self.__key: return
        if message[4] not in (1, 2,): return

        if message[4] == 2:
            self.handle_cmd_msg(message[5:])
        else:
            self.dispatcher.send_msg_to_tunnel(message[5:])

    def udp_writable(self):
        self.remove_evt_write(self.fileno)

    def udp_delete(self):
        self.unregister(self.fileno)
        self.close()

    def send_ip_msg(self, message: bytes):
        if self.__port < 1: return
        wrap_data = b"".join([struct.pack("!4sB", self.__key, 1), message])
        self.sendto(wrap_data, ("1271.0.0.1", self.__port))
        self.add_evt_write(self.fileno)

    def tell_peer_port(self):
        """告知对端端口号
        """
        pass
