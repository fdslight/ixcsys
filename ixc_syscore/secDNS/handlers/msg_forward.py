#!/usr/bin/env python3
import os, socket
import pywind.evtframework.handlers.udp_handler as udp_handler


class msg_fwd(udp_handler.udp_handler):
    __key = None
    __from_port = None

    def init_func(self, creator):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.set_socket(s)
        self.bind(("127.0.0.1", 0))

        self.__key = self.rand_key()
        self.register(self.fileno)
        self.add_evt_read(self.fileno)

        return self.fileno

    def rand_key(self):
        return os.urandom(4)

    @property
    def key(self):
        return self.__key

    @property
    def port(self):
        return self.socket.getsockname()[1]

    def udp_readable(self, message, address):
        if message[0:4] != self.key: return
        self.__from_port = address[1]
        message = message[4:]
        self.dispatcher.handle_msg_from_local(message)

    def send_msg_to_local(self, message: bytes):
        if self.__from_port is None: return
        # 接收需要使用key,发送则不需要
        print(message)
        self.sendto(message, ("127.0.0.1", self.__from_port))
        self.add_evt_write(self.fileno)

    def udp_writable(self):
        self.remove_evt_write(self.fileno)

    def udp_error(self):
        self.delete_handler(self.fileno)

    def udp_delete(self):
        self.unregister(self.fileno)
        self.close()
