#!/usr/bin/env python3

import socket
import pywind.evtframework.handlers.tcp_handler as tcp_handler
import pywind.web.lib.httputils as httputils
import pywind.lib.netutils as netutils


class tcp_listener(tcp_handler.tcp_handler):
    def init_func(self, creator_fd, listen, is_unix_socket=False, is_ipv6=False):
        if is_ipv6:
            fa = socket.AF_INET6
        else:
            fa = socket.AF_INET

        if is_unix_socket: fa = socket.AF_UNIX

        s = socket.socket(fa, socket.SOCK_STREAM)

        if not is_unix_socket:
            if is_ipv6: s.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.set_socket(s)
        self.bind(listen)
        self.listen(10)
        self.register(self.fileno)
        self.add_evt_read(self.fileno)

        return self.fileno

    def tcp_accept(self):
        while 1:
            try:
                cs, caddr = self.accept()
            except BlockingIOError:
                break
            self.create_handler(self.fileno, cs, caddr)
        return

    def tcp_error(self):
        pass

    def tcp_delete(self):
        self.unregister(self.fileno)
        self.close()


class tcp_proxy_handler(tcp_handler.tcp_handler):
    __handleshake_ok = None
    __caddr = None

    def init_func(self, creator_fd, cs, caddr):
        self.__handleshake_ok = False
        self.set_socket(cs)
        self.__caddr = caddr

        return self.fileno

    def handle_handshake_request(self):
        size = self.reader.size()
        byte_data = self.reader.read()
        p = byte_data.find(b"\r\n\r\n")

        if size > 4096 and p < 0:
            self.delete_handler(self.fileno)
            return

        p += 4
        request, kv_pairs = httputils.parse_htt1x_request_header(byte_data[0:p].decode("iso-8859-1"))
        method, host, version = request

        if method != "CONNECT":
            self.send_handshake_response("400 Bad Request")
            self.delete_this_no_sent_data()
            return

        is_domain = False
        is_ipv6 = netutils.is_ipv6_address(host)
        is_ipv4 = netutils.is_ipv4_address(host)

        if not is_ipv4 and not is_ipv6: is_domain = True

    def send_handshake_response(self, status: str):
        kv_pairs = [
            ("Server", "ixcsys_proxy_server"),
        ]

        s = httputils.build_http1x_resp_header(status, kv_pairs)

        self.writer.write(s.encode("iso-8859-1"))
        self.add_evt_write(self.fileno)

    def handle_connect(self, src_addr: tuple, dst_addr: tuple, is_domain=False, is_ipv6=False):
        """处理连接,重写这个方法
        @param src_addr:
        @param dst_addr:
        @param is_domain:
        @param is_ipv6:
        @return:
        """
        pass

    def handle_data(self, win_size: int, message: bytes):
        """处理数据,重写这个方法
        @param win_size:
        @param message:
        @return:
        """
        pass

    def tcp_readable(self):
        if not self.__handleshake_ok:
            self.handle_handshake_request()
        if not self.__handleshake_ok: return

    def tcp_writable(self):
        pass

    def tcp_error(self):
        pass

    def tcp_delete(self):
        self.unregister(self.fileno)
