#!/usr/bin/env python3
import socket, time

import pywind.evtframework.handlers.tcp_handler as tcp_handler
import pywind.evtframework.handlers.ssl_handler as ssl_handler

import pywind.web.lib.httputils as httputils

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

    # HTTP1x版本是否保持连接
    __http1_keep_conn = None
    __http1_parssed_header = None
    __scgi_closed = None

    # 连接超时时间
    __conn_timeout = None
    # 最近更新事件
    __time_up = None

    __sessions = None

    # SSL会话句柄
    __ssl_context = None

    __is_error = None

    def ssl_init(self, cs, caddr, ssl_on=False, ssl_key=None, ssl_cert=None, is_ipv6=False):
        self.__ssl_on = ssl_on
        self.__ssl_cert = ssl_cert
        self.__ssl_key = ssl_key
        self.__caddr = caddr

        self.__http_version = 1
        self.__http1_parssed_header = False
        self.__scgi_closed = False

        self.__conn_timeout = 120
        self.__time_up = time.time()

        self.__sessions = {}
        self.__is_error = False

        if ssl_on:
            self.set_ssl_on()

        self.set_socket(cs)
        self.register(self.fileno)
        self.add_evt_read(self.fileno)

        self.set_timeout(self.fileno, 10)

        return self.fileno

    def ssl_handshake_ok(self):
        pass

    def kv_pairs_value_get(self, name: str, kv_pairs: list, default=None):
        result = default

        for x, value in kv_pairs:
            t_name = x.lower()
            if t_name == name.lower():
                result = value
                break
            ''''''

        return result

    def convert_to_cgi_env(self, request: tuple, kv_pairs: list):
        """转换成CGI环境变量
        """
        env={
            "REQUEST_METHOD":request[0].upper(),
            "REQUEST_URI":request[1],
        }

        return env

    def http1_header_send(self, status: str, kv_pairs: list):
        pass

    def http1_body_send(self, body_data: bytes):
        pass

    def http1_finish(self):
        if not self.__http1_keep_conn:
            self.delete_this_no_sent_data()
            return
        self.__http1_parssed_header = False

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

    def handle_http_request_header(self, xid, request: tuple, kv_pairs: list):
        # 检查头部格式是否合法
        method, url, version = request
        content_length = self.kv_pairs_value_get("content-length", kv_pairs)

        # 检查HTTP请求方法是否支持
        methods = (
            "GET", "POST", "PUT", "DELETE", "CONNECT",
        )

        if method not in methods:
            self.__is_error = True
            self.send_header(xid, "405 Method Not Allowed", [])
            self.delete_this_no_sent_data()
            return

        if method in ("POST", "PUT",) and content_length == None:
            self.__is_error = True
            self.send_header(HTTP1_xID, "411 Length Required", [])
            self.delete_this_no_sent_data()
            return

        # 检查content-length是否为数字
        try:
            int(content_length)
        except ValueError:
            self.__is_error = True
            self.send_header(xid, "400 Bad Request", [])
            self.delete_this_no_sent_data()
            return

        # 必须要有host字段
        host = self.kv_pairs_value_get("host", kv_pairs)
        if host == None:
            self.__is_error = True
            self.send_header(xid, "400 Bad Request", [])
            self.delete_this_no_sent_data()
            return

        # 必须要有user-agent字段
        user_agent = self.kv_pairs_value_get("user-agent", kv_pairs)
        if user_agent == None:
            self.__is_error = True
            self.send_header(xid, "400 Bad Request", [])
            self.delete_this_no_sent_data()
            return

        if self.__http_version == 1:
            self.__http1_parssed_header = True
        # 此处打开SCGI会话

    def parse_http1_request_header(self):
        size = self.reader.size()
        rdata = self.reader.read()

        p = rdata.find(b"\r\n\r\n")
        # 限制请求头部长度
        if p < 0 and size > 4096:
            self.__is_error = True
            self.send_header(HTTP1_xID, "400 Bad Request", [])
            self.delete_this_no_sent_data()
            return

        p += 4
        byte_header_s = rdata[0:p]
        self.reader._putvalue(rdata[p:])

        try:
            request, kv_pairs = httputils.parse_htt1x_request_header(byte_header_s.decode("iso-8859-1"))
        except httputils.Http1xHeaderErr:
            self.__is_error = True
            self.send_header(HTTP1_xID, "400 Bad Request", [])
            self.delete_this_no_sent_data()
            return
        self.handle_http_request_header(HTTP1_xID, request, kv_pairs)

    def handle_http1_request_body(self):
        scgi_fd, cls = self.__sessions[HTTP1_xID]

    def handle_http1_request(self):
        if not self.__http1_parssed_header:
            self.parse_http1_request_header()
        if not self.__http1_parssed_header:
            return
        self.handle_http1_request_body()

    def handle_http2_request(self):
        pass

    def tcp_readable(self):
        # 发生错误直接丢弃读取的数据包,避免客户端恶意发送大量数据包导致消耗内存过大
        if self.__is_error:
            self.reader.read()
            return
        if self.__http_version == 1:
            self.handle_http1_request()
        else:
            self.handle_http2_request()

    def tcp_writable(self):
        pass

    def tcp_timeout(self):
        pass

    def tcp_error(self):
        pass

    def tcp_delete(self):
        pass
