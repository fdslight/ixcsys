#!/usr/bin/env python3

import socket
import pywind.evtframework.handlers.udp_handler as udp_handler

import ixc_syscore.netdog.pylib.sys_msg as libsys_msg


class sys_msg(udp_handler.udp_handler):
    def init_func(self, creator_fd):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.set_socket(s)
        self.connect(("127.0.0.1", 8965))
        self.register(self.fileno)
        self.add_evt_read(self.fileno)

        return self.fileno

    def udp_readable(self, message, address):
        try:
            _type, msg = libsys_msg.unwrap_sys_msg(message)
        except libsys_msg.SYS_MSG_Error:
            return

        print(msg)

    def udp_writable(self):
        self.remove_evt_write(self.fileno)

    def udp_error(self):
        pass

    def udp_timeout(self):
        pass

    def udp_delete(self):
        self.unregister(self.fileno)
        self.close()

    def send_msg(self, _type: int, msg: bytes):
        wrap_msg = libsys_msg.wrap_sys_msg(_type, msg)
        self.add_evt_write(self.fileno)
        self.send(wrap_msg)
