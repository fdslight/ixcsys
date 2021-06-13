#!/usr/bin/env python3
"""日志接收
"""
import socket, pickle
import pywind.evtframework.handlers.udp_handler as udp_handler


class syslogd(udp_handler.udp_handler):
    def init_func(self, creator_fd):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.set_socket(s)
        self.bind(("127.0.0.1", 1999))
        self.register(self.fileno)
        self.add_evt_read(self.fileno)

        return self.fileno

    def udp_readable(self, message, address):
        if address[0] != "127.0.0.1": return
        try:
            brd_content = pickle.loads(message)
        except:
            return
        if not isinstance(brd_content, dict): return

    def udp_writable(self):
        pass

    def udp_error(self):
        pass

    def udp_delete(self):
        self.unregister(self.fileno)
        self.close()
