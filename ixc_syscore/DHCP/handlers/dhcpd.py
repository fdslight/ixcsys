#!/usr/bin/env python3

import socket, struct
import pywind.evtframework.handlers.udp_handler as udp_handler


class dhcp_service(udp_handler.udp_handler):
    __sock_info = None
    __id = None
    __server_port = None

    __dhcp_server = None
    __dhcp_client = None

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

    def udp_writable(self):
        self.remove_evt_write(self.fileno)

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

    def send_dhcp_msg(self, _id: bytes, flags: int, message: bytes):
        header = struct.pack("!16sHbb", _id, 0x0800, 0, flags)
        sent_msg = b"".join([header, message])

        self.add_evt_write(self.fileno)
        self.sendto(sent_msg, ("127.0.0.1", self.__server_port))
