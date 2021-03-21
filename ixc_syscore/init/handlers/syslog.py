#!/usr/bin/env python3
"""日志接收
"""
import socket, pickle
import pywind.evtframework.handlers.udp_handler as udp_handler
import ixc_syslib.pylib.logging as logging


class syslogd(udp_handler.udp_handler):
    def init_func(self, creator_fd):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.set_socket(s)
        self.bind(("127.0.0.1", 514))
        self.register(self.fileno)
        self.add_evt_read(self.fileno)

        return self.fileno

    def udp_readable(self, message, address):
        if address[0] != "127.0.0.1": return
        try:
            log_info = pickle.loads(message)
        except:
            return
        if not isinstance(log_info, dict): return
        try:
            level = int(log_info["level"])
            app_name = log_info["name"]
            message = log_info["message"]
        except KeyError:
            return
        except ValueError:
            return
        if level not in logging.LEVELS: return
        self.dispatcher.log_write(level, app_name, message)

    def udp_writable(self):
        pass

    def udp_error(self):
        pass

    def udp_delete(self):
        self.unregister(self.fileno)
        self.close()
