#!/usr/bin/env python3

import socket
import pywind.evtframework.handlers.udp_handler as udp_handler


class dhcp_service(udp_handler.udp_handler):
    __sock_info = None
    __id = None
    __server_port = None

    def init_func(self, creator_fd):
        self.__server_port = -1

        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        self.set_socket(s)
        self.bind(("127.0.0.1", 0))
        self.__sock_info = s.getsockname()
        self.register(self.fileno)
        self.add_evt_read(self.fileno)

        return self.fileno

    def udp_readable(self, message, address):
        if address[0] != "127.0.0.1": return
        if address[1] != self.__server_port: return
        print(message)

    def udp_writable(self):
        pass

    def udp_error(self):
        self.delete_handler(self.fileno)

    def udp_delete(self):
        self.unregister(self.fileno)
        self.close()

    def get_sock_port(self):
        return self.__sock_info[1]

    def set_message_auth(self, _id: bytes, server_port: int):
        """设置消息认证
        :param _id:
        :param server_port:
        :return:
        """
        self.__id = _id
        self.__server_port = server_port
