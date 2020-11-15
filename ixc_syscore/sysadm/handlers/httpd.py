#!/usr/bin/env python3
import socket, time, os

import pywind.evtframework.handlers.tcp_handler as tcp_handler
import pywind.evtframework.handlers.ssl_handler as ssl_handler

import pywind.web.lib.httputils as httputils

HTTP1_xID = 0


def slice_bytes(byte_data: bytes, slice_size=3072):
    results = []
    a, b = (0, slice_size,)
    while 1:
        t = byte_data[a:b]
        if not t: break
        a = b
        b += slice_size
        results.append(t)

    return results


class SCGIClient(tcp_handler.tcp_handler):
    __xid = None
    __env = None
    __sent = None
    __creator_fd = None
    __is_resp_header = None
    __up_time = None
    __conn_timeout = None

    def get_app_path_info(self, path_info: str):
        if path_info == "/": return (os.getenv("IXC_MYAPP_NAME"), path_info,)

        p = path_info[1:].find("/")
        if p < 0: return (os.getenv("IXC_MYAPP_NAME"), path_info)
        p += 1

        return path_info[1:p], path_info[p:]

    def get_scgi_path(self, path_info: str):
        rs = self.get_app_path_info(path_info)
        app_name, url = rs

        return "/tmp/ixcsys/%s/scgi.sock" % app_name

    def init_func(self, creator_fd, xid: int, cgi_env: dict):
        self.__creator_fd = creator_fd
        self.__xid = xid
        self.__env = cgi_env
        self.__sent = []
        self.__is_resp_header = False
        self.__up_time = time.time()
        self.__conn_timeout = 120

        address = self.get_scgi_path(cgi_env["PATH_INFO"])
        if not os.path.exists(address): return -1

        # 重写PATH INFO
        _, path_info = self.get_app_path_info(cgi_env["PATH_INFO"])
        self.__env["PATH_INFO"] = path_info

        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.set_socket(s)
        self.connect(address)
        self.__send_scgi_header()

        return self.fileno

    def connect_ok(self):
        self.register(self.fileno)
        self.add_evt_read(self.fileno)
        self.add_evt_write(self.fileno)
        self.set_timeout(self.fileno, 10)

    def tcp_readable(self):
        if not self.__is_resp_header:
            self.handle_resp_header()
        if self.__is_resp_header:
            self.handle_resp_body()

    def tcp_writable(self):
        if self.__sent:
            self.writer.write(self.__sent.pop(0))
        if self.writer.size() == 0:
            self.remove_evt_write(self.fileno)

    def tcp_timeout(self):
        if not self.is_conn_ok():
            self.get_handler(self.__creator_fd).handle_scgi_error(self.__xid)
            return
        t = time.time()
        if t - self.__up_time > self.__conn_timeout:
            self.get_handler(self.__creator_fd).handle_scgi_error(self.__xid)
            return
        self.set_timeout(self.fileno, 10)

    def tcp_error(self):
        if not self.__is_resp_header:
            self.get_handler(self.__creator_fd).handle_scgi_error(self.__xid)
            return
        self.handle_resp_body()
        self.get_handler(self.__creator_fd).handle_scgi_resp_finish(self.__xid)

    def tcp_delete(self):
        self.unregister(self.fileno)
        self.close()

    def handle_resp_header(self):
        self.__up_time = time.time()

        size = self.reader.size()
        rdata = self.reader.read()
        p = rdata.find(b"\r\n\r\n")

        if p < 0 and size > 8192:
            self.get_handler(self.__creator_fd).handle_scgi_error(self.__xid)
            return

        p += 4
        self.reader._putvalue(rdata[p:])
        s = rdata[0:p].decode("iso-8859-1")
        tp = s.split("\r\n\r\n")
        _list = []

        for s in tp:
            if not s: continue
            _list.append(s)

        kv_pairs = []

        for s in _list:
            p = s.find(":")
            if p < 0:
                self.get_handler(self.__creator_fd).handle_scgi_error(self.__xid)
                return
            name = s[0:p]
            p += 1
            value = s[p:].strip()
            kv_pairs.append((name, value,))

        name, status = kv_pairs.pop(0)

        if name.lower() != "status":
            self.get_handler(self.__creator_fd).handle_scgi_error(self.__xid)
            return

        try:
            int(status[0:3])
        except ValueError:
            self.get_handler(self.__creator_fd).handle_scgi_error(self.__xid)
            return

        self.get_handler(self.__creator_fd).handle_scgi_resp_header(self.__xid, status, kv_pairs)
        self.__is_resp_header = True

    def handle_resp_body(self):
        self.__up_time = time.time()
        rdata = self.reader.read()
        self.get_handler(self.__creator_fd).handle_scgi_resp_body(self.__xid, rdata)

    def send_data(self, byte_data: bytes):
        if not byte_data: return
        self.__sent += slice_bytes(byte_data)
        if self.is_conn_ok(): self.add_evt_write(self.fileno)

    def __send_scgi_header(self):
        content_length = int(self.__env["CONTENT_LENGTH"])

        del self.__env["CONTENT_LENGTH"]

        tp = [
            "CONTENT_LENGTH", str(content_length),
            "SCGI", str(1),
        ]

        for name, value in self.__env.items():
            tp.append(name)
            tp.append(value)

        s = "\0".join(tp)
        byte_s = s.encode()
        tot_len = len(byte_s) + content_length

        x = "%d:" % tot_len
        sent_data = b"".join([x.encode(), byte_s, b","])
        self.send_data(sent_data)

    def send_scgi_body(self, byte_data: bytes):
        self.send_data(byte_data)


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
        self.register(self.fileno)
        self.add_evt_read(self.fileno)

        return self.fileno

    def tcp_accept(self):
        while 1:
            try:
                cs, caddr = self.accept()
            except BlockingIOError:
                break
            self.create_handler(self.fileno, httpd_handler, cs, caddr, ssl_on=self.__ssl_on, ssl_key=self.__ssl_key,
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

    __SERVER = None

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

        self.__SERVER = "ixcsys"

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
        env = {
            "REQUEST_METHOD": request[0].upper(),
            "REQUEST_URI": request[1],
            "QUERY_STRING": ""
        }

        request_uri = request[1]
        p = request_uri.find("?")

        if p > 0:
            env["PATH_INFO"] = request_uri[0:p]
            p += 1
            env["QUERY_STRING"] = request_uri[p:]
        else:
            env["PATH_INFO"] = request_uri
        env["SERVER_PROTOCOL"] = request[2].upper()

        excepts = ("content_length", "content_type",)
        for k, v in kv_pairs:
            k = k.replace("-", "_")
            if k.lower() not in excepts:
                k = "HTTP_%s" % k.upper()
            env[k.upper()] = v

        if "CONTENT_LENGTH" not in env: env["CONTENT_LENGTH"] = "0"

        # 设置RPC不可用
        env["HTTP_X_IXCSYS_RPC"] = "0"
        env["REMOTE_ADDR"] = self.socket.getsockname()[0]

        return env

    def http1_header_send(self, status: str, kv_pairs: list):
        s = httputils.build_http1x_resp_header(status, kv_pairs)
        self.writer.write(s.encode())
        self.add_evt_write(self.fileno)

    def http1_body_send(self, body_data: bytes):
        self.writer.write(body_data)
        self.add_evt_write(self.fileno)

    def http1_finish(self):
        if not self.__http1_keep_conn:
            self.delete_this_no_sent_data()
            return
        self.__http1_parssed_header = False

    def http2_header_send(self, xid: int, status: str, kv_pairs: list):
        pass

    def http2_body_send(self, xid: int, body_data: bytes):
        pass

    def http2_finish(self, xid: int):
        pass

    def http_finish(self, xid: int):
        fd, cls = self.__sessions[xid]

        if self.__http_version == 1:
            self.http1_finish()
        else:
            self.http2_finish(xid)

        self.delete_handler(fd)

    def send_header(self, xid: int, status: str, kv_pairs: list):
        self.__time_up = time.time()

        drop_names = ("server",)
        new_kv_pairs = []

        for name, value in kv_pairs:
            if name.lower() in drop_names: continue
            new_kv_pairs.append((name, value,))

        new_kv_pairs.append(("Server", self.__SERVER,))

        if self.__http_version == 1:
            self.http1_header_send(status, new_kv_pairs)
        else:
            self.http2_header_send(xid, status, new_kv_pairs)

    def send_body(self, xid: int, body_data: bytes):
        self.__time_up = time.time()

        if self.__http_version == 1:
            self.http1_body_send(body_data)
        else:
            self.http2_body_send(xid, body_data)

    def handle_scgi_resp_header(self, xid: int, status: int, kv_pairs: list):
        self.send_header(xid, status, kv_pairs)

    def handle_scgi_resp_body(self, xid: int, body_data: bytes):
        self.send_body(xid, body_data)

    def handle_scgi_resp_finish(self, xid: int):
        self.http_finish(xid)

    def handle_scgi_error(self, xid: int):
        self.send_header(xid, "502 Bad Gateway", [])
        self.http_finish(xid)

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
            length = int(content_length)
        except ValueError:
            self.__is_error = True
            self.send_header(xid, "400 Bad Request", [])
            self.delete_this_no_sent_data()
            return
        # 当为None的时候报错忽略,因为前面已经检查过有些方法必须带长度,没有长度那么就是None
        except TypeError:
            length = 0

        # 除了POST和PUT外其他方法长度必须为0
        if method not in ("POST", "PUT",) and length != 0:
            self.__is_error = True
            self.send_header(HTTP1_xID, "411 Length Required", [])
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
        env = self.convert_to_cgi_env(request, kv_pairs)

        fd = self.create_handler(self.fileno, SCGIClient, xid, env)

        if fd < 0:
            self.__is_error = True
            self.send_header(xid, "502 Bad Gateway", [])
            self.delete_this_no_sent_data()
            return

        self.__sessions[xid] = (fd, None,)

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
        self.get_handler(scgi_fd).send_scgi_body(self.reader.read())

    def handle_http1_request(self):
        if not self.__http1_parssed_header:
            self.parse_http1_request_header()
        if not self.__http1_parssed_header:
            return
        if self.__is_error: return
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
        if self.writer.size() == 0: self.remove_evt_write(self.fileno)

    def tcp_timeout(self):
        t = time.time()
        if t - self.__time_up > self.__conn_timeout:
            self.delete_handler(self.fileno)
            return
        self.set_timeout(self.fileno, 10)

    def tcp_error(self):
        self.delete_handler(self.fileno)

    def tcp_delete(self):
        for xid in self.__sessions:
            fd, cls = self.__sessions[xid]
            self.delete_handler(fd)
        self.unregister(self.fileno)
        self.close()
