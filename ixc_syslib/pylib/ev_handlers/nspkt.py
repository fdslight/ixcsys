#!/usr/bin/env python3

import socket, struct
import pywind.evtframework.handlers.udp_handler as udp_handler


class nspkt_handler(udp_handler.udp_handler):
    __sock_info = None
    __id = None
    __server_port = None

    def init_func(self, creator_fd, *args, **kwargs):
        self.__server_port = -1
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        self.set_socket(s)
        self.bind(("127.0.0.1", 0))
        self.__sock_info = s.getsockname()
        self.register(self.fileno)
        self.add_evt_read(self.fileno)

        self.my_init(*args, **kwargs)

        return self.fileno

    def my_init(self, *args, **kwargs):
        """重写这个方法
        """
        pass

    def udp_readable(self, message, address):
        if address[0] != "127.0.0.1": return
        if address[1] != self.__server_port: return

        if len(message) < 34: return
        _id, if_type, _, ipproto, flags = struct.unpack("!16sBBBB", message[0:20])
        if _id != self.__id: return
        self.handle_recv(if_type, ipproto, flags, message[20:])

    def handle_recv(self, if_type: int, ipproto: int, flags: int, message: bytes):
        """处理接收数据,重写这个方法
        """
        pass

    def udp_writable(self):
        self.remove_evt_write(self.fileno)

    def udp_error(self):
        self.delete_handler(self.fileno)

    def udp_delete(self):
        self.unregister(self.fileno)
        self.close()

    def get_sock_port(self):
        return self.__sock_info[1]

    def set_message_auth(self, _id: bytes):
        """设置消息认证
        :param _id:
        :return:
        """
        self.__id = _id
        self.__server_port = 8964

    def send_msg(self, if_type: int, ipproto: int, flags: int, message: bytes):
        header = struct.pack("!16sBBBB", self.__id, if_type, 0, ipproto, flags)
        sent_msg = b"".join([header, message])

        self.add_evt_write(self.fileno)
        self.sendto(sent_msg, ("127.0.0.1", self.__server_port))
        self.send_now()
