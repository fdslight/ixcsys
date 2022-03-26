#!/usr/bin/env python3
import os, socket, time
import pywind.evtframework.handlers.udp_handler as udp_handler
import ixc_syscore.sysadm.pylib.n2n as n2n


class n2nd(udp_handler.udp_handler):
    """接收未处理过的UDP数据包
    """
    __redirect_address = None
    __parser = None
    __builder = None

    __remote_address = None
    __time = None

    def init_func(self, creator_fd, address, remote_addr, redir_addr, is_ipv6=False):
        self.__parser = n2n.parser()
        self.__builder = n2n.builder()

        self.__redirect_address = redir_addr
        self.__remote_address = remote_addr
        self.__time = time.time()

        if is_ipv6:
            fa = socket.AF_INET6
        else:
            fa = socket.AF_INET

        s = socket.socket(fa, socket.SOCK_DGRAM)
        if is_ipv6: s.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self.set_socket(s)
        self.bind(address)
        self.register(self.fileno)
        self.add_evt_read(self.fileno)
        self.set_timeout(self.fileno, 10)

        return self.fileno

    def handle_from_lan(self, message: bytes):
        """处理来自于LAN的数据
        :param message:
        :return:
        """
        wrap_data = self.__builder.build(n2n.TYPE_DATA, message)
        self.sendto(wrap_data, self.__remote_address)
        self.add_evt_write(self.fileno)

    def handle_ping(self):
        wrap_data = self.__builder.build(n2n.TYPE_PONG, os.urandom(32))
        self.sendto(wrap_data, self.__remote_address)
        self.add_evt_write(self.fileno)

    def send_ping(self):
        wrap_data = self.__builder.build(n2n.TYPE_PING, os.urandom(32))
        self.sendto(wrap_data, self.__remote_address)
        self.add_evt_write(self.fileno)

    def handle_from_wan(self, message: bytes):
        """处理来自于WAN的数据
        :param message:
        :return:
        """
        rs = self.__parser.parse(message)
        if not rs: return
        _type, msg = rs

        if _type == n2n.TYPE_PING:
            self.handle_ping()
            return

        if _type == n2n.TYPE_DATA:
            self.sendto(msg, self.__redirect_address)
            self.add_evt_write(self.fileno)
            return

    def udp_readable(self, message, address):
        if address[0] == self.__remote_address[0] and address[1] == self.__remote_address[1]:
            self.handle_from_wan(message)
            return
        if address[0] == self.__redirect_address[0] and address[1] == self.__redirect_address[1]:
            self.handle_from_lan(message)
            return

    def udp_writable(self):
        self.remove_evt_write(self.fileno)

    def udp_delete(self):
        self.unregister(self.fileno)
        self.close()

    def udp_timeout(self):
        now_time = time.time()
        # 每隔60s发送一次ping
        if now_time - self.__time >= 60:
            self.send_ping()
            self.__time = now_time
        self.set_timeout(self.fileno, 10)
