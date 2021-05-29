#!/usr/bin/env python3
import socket, time, random

import pywind.evtframework.handlers.ssl_handler as ssl_handler
import pywind.web.lib.httputils as httputils
import pywind.web.lib.websocket as wslib

import ixc_syslib.pylib.logging as logging
import ixc_syscore.sysadm.pylib.cloud_service as cloud_service_protocol


class cloud_service_client(ssl_handler.ssl_handler):
    __http_handshake_ok = None
    __host = None
    __port = None
    __http_handshake_key = None

    __parser = None
    __builder = None

    def ssl_init(self, host: str, port: int, is_ipv6=False):
        self.__http_handshake_ok = False
        self.__port = port
        self.__http_handshake_key = None

        self.__parser = cloud_service_protocol.parser(self.key)
        self.__builder = cloud_service_protocol.builder(self.key)

        if is_ipv6:
            fa = socket.AF_INET6
        else:
            fa = socket.AF_INET

        s = socket.socket(fa, socket.SOCK_STREAM)
        self.set_socket(s)
        self.connect((host, port))

        return self.fileno

    def connect_ok(self):
        self.register(self.fileno)
        self.add_evt_read(self.fileno)
        self.add_evt_write(self.fileno)
        # self.set_ssl_on()

    def ssl_handshake_ok(self):
        pass

    def tcp_readable(self):
        pass

    def tcp_writable(self):
        if self.writer.size() == 0: self.remove_evt_write(self.fileno)

    @property
    def device_id(self):
        return self.dispatcher.cloud_service_device_id

    @property
    def key(self):
        """通信密钥
        """
        return self.dispatcher.cloud_service_key

    def send_http_request(self):
        kv_pairs = [
            ("Connection", "Upgrade"), ("Upgrade", "websocket",), (
                "User-Agent", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:69.0) Gecko/20100101 Firefox/69.0",),
            ("Accept-Language", "zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2"),
            ("Sec-WebSocket-Version", 13,), ("Sec-WebSocket-Key", self.rand_string(),),
            ("Sec-WebSocket-Protocol", "cloudservice"),
            ("X-IXC-Device-ID", self.device_id),
            ("X-IXC-Key", self.key),
        ]

        if self.__port == 443:
            host = ("Host", self.__host,)
            origin = ("Origin", "https://%s" % self.__host)
        else:
            host = ("Host", "%s:%s" % self.__host, self.__port)
            origin = ("Origin", "https://%s:%s" % self.__host, self.__port,)

        kv_pairs.append(host)
        kv_pairs.append(origin)

        s = httputils.build_http1x_req_header("GET", "/", kv_pairs)

        self.writer.write(s.encode("iso-8859-1"))
        self.add_evt_write(self.fileno)

    def recv_handshake(self):
        size = self.reader.size()
        data = self.reader.read()

        p = data.find(b"\r\n\r\n")

        if p < 10 and size > 2048:
            self.delete_handler(self.fileno)
            return

        if p < 0:
            self.reader._putvalue(data)
            return
        p += 4

        self.reader._putvalue(data[p:])

        s = data[0:p].decode("iso-8859-1")

        try:
            resp, kv_pairs = httputils.parse_http1x_response_header(s)
        except httputils.Http1xHeaderErr:
            self.delete_handler(self.fileno)
            return

        version, status = resp

        if status.find("101") != 0:
            self.delete_handler(self.fileno)
            return

        accept_key = self.get_http_kv_pairs("sec-websocket-accept", kv_pairs)
        if wslib.gen_handshake_key(self.__http_handshake_key) != accept_key:
            self.delete_handler(self.fileno)
            return

        self.__http_handshake_ok = True

    def get_http_kv_pairs(self, name, kv_pairs):
        for k, v in kv_pairs:
            if name.lower() == k.lower():
                return v
            ''''''
        return None

    def rand_string(self, length=8):
        seq = []
        for i in range(length):
            n = random.randint(65, 122)
            seq.append(chr(n))

        s = "".join(seq)
        self.__http_handshake_key = s

        return s

    def tcp_error(self):
        pass

    def tcp_timeout(self):
        pass

    def tcp_delete(self):
        pass

    def handle_rpc_request(self, fn: str, *args, **kwargs):
        """处理RPC请求
        """
        pass
