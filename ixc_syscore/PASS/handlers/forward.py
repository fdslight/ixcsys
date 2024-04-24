#!/usr/bin/env python3
"""数据帧格式
action:1 byte
    0表示notify,由客户端发出,告知客户端自身的名字以及端口,该数据包客户端定时更新
        数据格式为
            IXCSYS\r\n\r\n
            ClientName
    8表示以太网数据包
"""

import socket
import pywind.evtframework.handlers.udp_handler as udp_handler
import ixc_syslib.pylib.logging as logging


class forward_handler(udp_handler.udp_handler):
    __client_address = None
    __device_name = None

    def init_func(self, creator_fd, *args, **kwargs):
        self.__device_name = "no device"
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        self.set_socket(s)
        self.bind((self.dispatcher.manage_addr, 1999))
        self.register(self.fileno)
        self.add_evt_read(self.fileno)

        return self.fileno

    def handle_notify(self, message: bytes, address: str):
        p = message.find(b"\r\n\r\n")
        if p < 0:
            logging.print_error("wrong ixcpass notify packet")
            return
        try:
            magic_str = message[0:p].decode()
        except:
            logging.print_error("wrong ixcpass notify magic string decode")
            return

        if magic_str != "IXCSYS":
            logging.print_error("wrong ixcpass notify magic string")
            return
        p += 4

        device_name = message[p:].decode(errors="ignore")
        if not device_name:
            logging.print_alert("wrong ixcpass notify device name")
            return
        self.__device_name = device_name
        self.__client_address = address

    def udp_readable(self, message, address):
        if message[0] != 0 and not self.__client_address: return
        if message[0] == 0:
            self.handle_notify(message[1:], address)
            return
        if message[0] != 8:
            return

        self.dispatcher.send_message_to_router(message[1:])

    def send_msg(self, message: bytes):
        if not self.__client_address: return
        self.sendto(message, self.__client_address)
        self.add_evt_write(self.fileno)

    def udp_writable(self):
        self.remove_evt_write(self.fileno)

    def udp_error(self):
        self.delete_handler(self.fileno)

    def udp_delete(self):
        self.unregister(self.fileno)
        self.close()

    @property
    def device_name(self):
        return self.__device_name
