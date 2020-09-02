#!/usr/bin/env python3
import socket, time
import pywind.evtframework.handlers.tcp_handler as tcp_handler
import pywind.evtframework.handlers.ssl_handler as ssl_handler

HTTP1_xID = 0


class SCGIClient(tcp_handler.tcp_handler):
    __xid = None

    def init_func(self, creator_fd, xid: int, address):
        self.__xid = xid
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.set_socket(s)
        self.connect(address)

        return self.fileno

    def connect_ok(self):
        self.register(self.fileno)
        self.add_evt_read(self.fileno)

    def tcp_readable(self):
        pass

    def tcp_writable(self):
        pass

    def tcp_timeout(self):
        pass

    def tcp_delete(self):
        pass

    def send_request_header(self, cgi_env: dict):
        pass

    def send_body(self, byte_data: bytes):
        pass

    def handle_resp_header(self):
        pass

    def handle_resp_body(self):
        pass


class httpd_listener(tcp_handler.tcp_handler):
    __ssl_on = None
    __ssl_key = None
    __ssl_cert = None
    __is_ipv6 = None

    def init_func(self, creator_fd, address, is_ipv6=False, ssl_on=False, ssl_key=None, ssl_cert=None):
        self.__is_ipv6 = is_ipv6
        self.__ssl_on = ssl_on
        self.__ssl_key = ssl_key
        self.__ssl_cert = ssl_cert

        if is_ipv6:
            fa = socket.AF_INET6
        else:
            fa = socket.AF_INET
        s = socket.socket(fa, socket.SOCK_STREAM)
        if is_ipv6: s.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self.set_socket(s)
        self.bind(address)
        self.listen(10)

        return self.fileno

    def tcp_accept(self):
        while 1:
            try:
                cs, caddr = self.accept()
            except BlockingIOError:
                break
            self.create_handler(self.fileno, cs, caddr, ssl_on=self.__ssl_on, ssl_key=self.__ssl_key,
                                ssl_cert=self.__ssl_cert, is_ipv6=self.__is_ipv6)
        ''''''

    def tcp_delete(self):
        self.unregister(self.fileno)
        self.close()


class httpd_handler(ssl_handler.ssl_handler):
    __ssl_on = None
    __ssl_cert = None
    __ssl_key = None
    __caddr = None

    # http协议的版本
    __http_version = 1
    # 是否定义了HTTP协议版本
    __is_defined_http_version = None

    # HTTP1x版本是否保持连接
    __http1_keep_conn = None
    __http1_parssed_header = None
    __scgi_closed = None

    # 连接超时时间
    __conn_timeout = None
    # 最近更新事件
    __time_up = None

    __sessions = None

    def ssl_init(self, cs, caddr, ssl_on=False, ssl_key=None, ssl_cert=None, is_ipv6=False):
        self.__ssl_on = ssl_on
        self.__ssl_cert = ssl_cert
        self.__ssl_key = ssl_key
        self.__caddr = caddr

        self.__http_version = 1
        self.__is_defined_http_version = False

        self.__http1_parssed_header = False
        self.__scgi_closed = False

        self.__conn_timeout = 120
        self.__time_up = time.time()

        self.__sessions = {}

        self.set_socket(cs)
        self.register(self.fileno)
        self.add_evt_read(self.fileno)

        self.set_timeout(self.fileno, 10)

        return self.fileno

    def http1_header_send(self, status: str, kv_pairs: list):
        pass

    def http1_body_send(self, body_data: bytes):
        pass

    def http1_finish(self):
        pass

    def http2_header_send(self, xid: int, status: str, kv_pairs: list):
        pass

    def http2_body_send(self, xid: int, status: str, kv_pairs: list):
        pass

    def http2_finish(self, xid: int):
        pass

    def send_header(self, xid: int, status: str, kv_pairs: list):
        pass

    def send_body(self, xid: int, body_data: list):
        pass

    def handle_scgi_resp_header(self, xid: int, status: int, kv_pairs: list):
        pass

    def handle_scgi_resp_body(self, xid: int, body_data: bytes):
        pass

    def handle_scgi_resp_finish(self, xid: int):
        pass

    def handle_scgi_error(self, xid: int):
        pass

    def tcp_readable(self):
        pass

    def tcp_writable(self):
        pass

    def tcp_timeout(self):
        pass

    def tcp_error(self):
        pass

    def tcp_delete(self):
        pass
