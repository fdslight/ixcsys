#!/usr/bin/env python3
"""客户端隧道实现
"""
import socket, time

import pywind.evtframework.handlers.udp_handler as udp_handler
import ixc_syscore.proxy.pylib.logging as logging
import ixc_syscore.proxy.pylib.racs as racs


class udp_tunnel(udp_handler.udp_handler):
    __LOOP_TIMEOUT = 10
    __update_time = 0
    __server_address = None

    __encrypt = None
    __decrypt = None

    __priv_key = None
    __tunnel_ok = None

    __address = None
    __enable = None

    __is_ipv6 = None

    def init_func(self, creator, address, is_ipv6=False):
        if is_ipv6:
            fa = socket.AF_INET6
        else:
            fa = socket.AF_INET

        s = socket.socket(fa, socket.SOCK_DGRAM)

        self.set_socket(s)

        if is_ipv6:
            self.bind(("::", 0))
        else:
            self.bind(("0.0.0.0", 0))

        self.__encrypt = racs.encrypt()
        self.__decrypt = racs.decrypt()
        self.__priv_key = None
        self.__tunnel_ok = False
        self.__address = address
        self.__enable = False
        self.__is_ipv6 = is_ipv6

        self.register(self.fileno)
        self.add_evt_read(self.fileno)

        self.set_timeout(self.fileno, self.__LOOP_TIMEOUT)

        return self.fileno

    def create_tunnel(self):
        server_ip = self.dispatcher.get_racs_server_ip(self.__address[0])

        if not server_ip: return False

        self.__server_address = (server_ip, self.__address[1],)
        self.__tunnel_ok = True

    def udp_readable(self, message, address):
        if not self.__tunnel_ok: return
        if not self.__server_address: return

        # 核对地址是否一致
        if self.__server_address[0] != address[0]: return
        if self.__server_address[1] != address[1]: return

        rs = self.__decrypt.unwrap(message)
        if not rs: return
        user_id, msg = rs

        if user_id != self.__priv_key: return
        if not msg:
            self.send_msg_to_tunnel(message)
            return
        self.dispatcher.send_to_local(message)

    def udp_writable(self):
        self.remove_evt_write(self.fileno)

    def udp_error(self):
        logging.print_general("udp_error", self.__server_address)
        self.delete_handler(self.fileno)

    def send_heartbeat(self):
        self.send_msg_to_tunnel(b"")

    def udp_timeout(self):
        t = time.time()
        v = t - self.__update_time

        if not self.__enable:
            self.set_timeout(self.fileno, self.__LOOP_TIMEOUT)
            return

        if not self.__tunnel_ok:
            self.create_tunnel()
            self.set_timeout(self.fileno, self.__LOOP_TIMEOUT)
            return

        if v > 60:
            self.send_heartbeat()
            self.set_timeout(self.fileno, self.__LOOP_TIMEOUT)
            self.__update_time = t
            return
        ''''''

    def udp_delete(self):
        self.unregister(self.fileno)
        self.close()
        if not self.__server_address: return

    def set_key(self, key: str):
        self.__encrypt.set_key(key)
        self.__decrypt.set_key(key)

    def set_priv_key(self, priv_key: str):
        self.__priv_key = racs.calc_str_md5(priv_key)

    def send_msg(self, message: bytes):
        if self.__server_address: return
        if self.__tunnel_ok: return

        wrap_data = self.__encrypt.wrap(self.__priv_key, message)

        self.sendto(wrap_data, self.__server_address)
        self.add_evt_write(self.fileno)

    def enable(self, enable):
        self.__enable = enable
