#!/usr/bin/env python3

import socket, base64, json, time, struct
import pywind.evtframework.handlers.udp_handler as udp_handler


class dns_proxy(udp_handler.udp_handler):
    __map = None

    def init_func(self, creator_fd):
        self.__map = {}
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        self.set_socket(s)
        self.bind(("127.0.0.1", 0))
        self.register(self.fileno)
        self.add_evt_read(self.fileno)
        self.set_timeout(self.fileno, 10)

        return self.fileno

    def udp_readable(self, message, address):
        if address[0] != "127.0.0.1": return
        if address[1] != 8964: return

        s = base64.b16decode(message)
        dic = json.loads(s)

        action = dic["action"]
        dns_msg = dic["message"]

        dns_id, = struct.unpack("!H", dns_msg[0:2])
        self.__map[dns_id] = {"time": time.time(), "action": action}
        self.dispatcher.send_dns_request_to_tunnel(dns_msg)

    def udp_writable(self):
        self.remove_evt_write(self.fileno)

    def get_port(self):
        return self.getsockname()[1]

    def udp_timeout(self):
        now = time.time()
        dels = []

        for dns_id in self.__map:
            o = self.__map[dns_id]
            t = o["time"]
            if now - t >= 3: dels.append(dns_id)

        for dns_id in dels: del self.__map[dns_id]

        self.set_timeout(self.fileno, 10)
