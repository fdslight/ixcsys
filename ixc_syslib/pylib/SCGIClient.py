#!/usr/bin/env python3

import socket

import pywind.lib.reader as reader


class SCGIErr(Exception): pass


class SCGIClient(object):
    __s = None
    # 总的发送长度
    __tot_sent_length = None
    # 已经发送的数据长度
    __sent_length = None
    __parsed_header = None
    __reader = None

    __resp_headers = None

    def __init__(self, address, is_ipv6=False, is_unix_socket=False):
        self.__tot_sent_length = 0
        self.__sent_length = 0
        self.__parsed_header = False
        self.__reader = reader.reader()

        if is_unix_socket:
            s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        else:
            if is_ipv6:
                fa = socket.AF_INET6
            else:
                fa = socket.AF_UNIX
            ''''''
            s = socket.socket(fa, socket.SOCK_STREAM)
        self.__s = s
        self.__s.connect(address)

    def send(self, byte_data: bytes):
        while 1:
            if not byte_data: break
            try:
                sent_size = self.__s.send(byte_data)
            except:
                raise SCGIErr("cannot send data to server")
            byte_data = byte_data[sent_size:]

    def send_scgi_header(self, request: tuple, cgi_env: dict):
        """发送SCGI头部
        :param request,(method,url,version,)
        """
        if "CONTENT_LENGTH" not in cgi_env:
            content_length = 0
        else:
            content_length = cgi_env["CONTENT_LENGTH"]
            del cgi_env["CONTENT_LENGTH"]

        content_length = int(content_length)
        self.__sent_length = 0
        self.__tot_sent_length = content_length

        headers = [
            ("CONTENT_LENGTH", content_length,),
            ("SCGI", 1),
        ]
        for name, value in cgi_env.items():
            headers.append((name, value,))

        seq = []
        for name, value in headers:
            seq.append(
                "%s\0%s\0" % (name, value,)
            )
        s = "".join(seq)
        byte_s = s.encode("iso-8859-1")
        tot_length = content_length + len(byte_s)
        seq2 = [
            "%d:" % tot_length,
            s,
            ","
        ]
        sent_s = "".join(seq2)
        self.send(sent_s.encode("iso-8859-1"))

    def send_scgi_body(self, body_data: bytes):
        v = self.__tot_sent_length - self.__sent_length
        byte_s = body_data[0:v]
        self.send(byte_s)
        self.__sent_length += len(byte_s)

    def handle_response_header(self):
        size = self.__reader.size()
        byte_data = self.__reader.read()
        p = byte_data.find(b"\r\n\r\n")

        if p < 0:
            if size > 4096: raise SCGIErr("SCGI response header is too long")
            self.__reader._putvalue(byte_data)
            return

        p += 4
        header_data = byte_data[0:p]
        self.__reader._putvalue(byte_data[p:])

        header_data_s = byte_data.decode("iso-8859-1")
        tmplist_a = header_data_s.split("\r\n")
        p = tmplist_a[0].lower().find("status")

        if p != 0:
            raise SCGIErr("wrong SCGI response header")

        tmplist_b = []

        for s in tmplist_a:
            if not s: continue
            tmplist_b.append(s)

        results = []
        for s in tmplist_b:
            p = s.find(":")
            if p < 0:
                raise SCGIErr("wrong SCGI response header")

            name = s[0:p]
            p += 1
            value = s[p:]
            results.append((name, value,))
        self.__resp_headers = results
        self.__parsed_header = True

    def handle_response_body(self):
        pass

    def handle_response_finish(self):
        pass

    def handle_response(self):
        conn_err = False
        while 1:
            try:
                recv_data = self.__s.recv(4096)
                self.__reader._putvalue(recv_data)
            except ConnectionError:
                conn_err = True

            if not self.__parsed_header:
                self.handle_response_header()

            if self.__parsed_header:
                self.handle_response_body()

            if conn_err:
                self.handle_response_finish()
                break
