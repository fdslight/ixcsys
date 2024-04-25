#!/usr/bin/env python3
"""数据帧格式
type:4 bytes
    0表示notify,由客户端发出,告知客户端自身的名字以及端口,该数据包客户端定时更新
        数据格式为
            IXCSYS\r\n\r\n
            ClientName
    8表示以太网数据包
"""

import socket, struct, time
import pywind.evtframework.handlers.udp_handler as udp_handler
import ixc_syslib.pylib.logging as logging


class forward_handler(udp_handler.udp_handler):
    __client_address = None
    __device_name = None
    __time = None

    def init_func(self, creator_fd, *args, **kwargs):
        self.__device_name = "no device"
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        self.set_socket(s)
        self.bind((self.dispatcher.manage_addr, 1999))
        self.register(self.fileno)
        self.add_evt_read(self.fileno)
        self.set_timeout(self.fileno, 10)
        self.__time = time.time()

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
        self.__time = time.time()
        self.__device_name = device_name
        self.__client_address = address

    def udp_readable(self, message, address):
        if len(message) < 7: return
        _type, = struct.unpack("!I", message[0:4])

        if _type != 0 and not self.__client_address: return
        if _type == 0:
            self.handle_notify(message[4:], address)
            return
        if _type != 8: return

        self.dispatcher.send_message_to_router(message[4:])

    def send_msg(self, message: bytes):
        if not self.__client_address: return
        new_msg = struct.pack("!I", 8) + message
        self.sendto(new_msg, self.__client_address)
        self.add_evt_write(self.fileno)

    def udp_writable(self):
        self.remove_evt_write(self.fileno)

    def udp_error(self):
        self.delete_handler(self.fileno)

    def udp_delete(self):
        self.unregister(self.fileno)
        self.close()

    def udp_timeout(self):
        # 超时重置客户端
        now = time.time()
        if now - self.__time > 300:
            self.__device_name = "no device"
            self.__client_address = None
        return

    @property
    def device(self):
        if not self.__client_address:
            return self.__device_name, ""
        return self.__device_name, self.__client_address[0]
