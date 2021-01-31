#!/usr/bin/env python3
import struct
import pywind.evtframework.handlers.tcp_handler as tcp_handler
import pywind.web.lib.httputils as httputils


class client(tcp_handler.tcp_handler):
    __is_ipv6 = None
    __session_id = None
    __sent = None

    __src_addr = None
    __dst_addr = None

    __handshake_ok = None

    def init_func(self, creator_fd, session_id: bytes, src_addr: tuple, dst_addr: tuple, proxy_server: tuple,
                  is_ipv6=False):
        self.__is_ipv6 = is_ipv6
        self.__session_id = session_id
        self.__sent = []
        self.__src_addr = src_addr
        self.__dst_addr = dst_addr

        self.__handshake_ok = False

        return self.fileno

    def send_conn_request(self):
        """发送连接请求
        @return:
        """
        s = httputils.build_http1x_req_header("CONNECT", self.dispatcher.http_proxy_url, [])
        self.writer.write(s.encode())
        self.add_evt_write(self.fileno)

    def handle_handshake_resp(self):
        """处理握手响应
        @return:
        """
        size = self.reader.size()
        byte_data = self.reader.read()
        p = byte_data.find(b"\r\n\r\n")

        if size > 4096 and p < 0:
            self.delete_handler(self.fileno)
            return
        p += 4
        vs, kv_pairs = httputils.parse_http1x_response_header(byte_data[0:p].decode("iso-8859-1"))
        # 此处检查是否建立连接成功
        version, st = vs
        if st[0:3] != "200":
            self.dispatcher.tcp_close(self.__session_id, is_ipv6=self.__is_ipv6)
            return
            # 握手成功的处理方式
        self.__handshake_ok = True
        self.handle_handshake_ok()

    def handle_handshake_ok(self):
        """
        @return:
        """
        ### 发送堆积的数据
        while 1:
            try:
                msg = self.__sent.pop(0)
            except IndexError:
                break
            self.writer.write(msg)
        self.add_evt_write(self.fileno)

    def connect_ok(self):
        self.register(self.fileno)
        self.add_evt_read(self.fileno)
        self.add_evt_write(self.fileno)

    def tcp_readable(self):
        if not self.__handshake_ok:
            self.handle_handshake_resp()
        if not self.__handshake_ok: return

        rdata = self.reader.read(0xffff)
        self.dispatcher.send_tcp_message(self.__session_id, rdata, is_ipv6=self.__is_ipv6)

    def tcp_writable(self):
        if self.writer.size() == 0: self.remove_evt_write(self.fileno)

    def send_to_proxy_server(self, window_size: int, message: bytes):
        seq = [
            struct.pack("!HH", window_size, len(message)),
            message
        ]
        if not self.__handshake_ok:
            self.__sent.append(b"".join(seq))
            return
        self.writer.write(b"".join(seq))
        self.add_evt_write(self.fileno)

    def tcp_error(self):
        self.dispatcher.tcp_close(self.__session_id, is_ipv6=self.__is_ipv6)

    def handle_close_callback(self):
        """重写这个方法,处理连接关闭
        @return:
        """
        self.delete_handler(self.fileno)

    def tcp_delete(self):
        self.unregister(self.fileno)
        self.close()
