#!/usr/bin/env python3
"""客户端隧道实现
"""

import socket, time, ssl
import struct

import pywind.evtframework.handlers.tcp_handler as tcp_handler
import pywind.lib.netutils as netutils
import ixc_syslib.pylib.logging as logging

import ixc_syslib.pylib.ssl_backports as ssl_backports


class dot_client(tcp_handler.tcp_handler):
    __LOOP_TIMEOUT = 10
    __update_time = 0
    __conn_timeout = 0
    __ssl_handshake_ok = None
    __hostname = ""

    __tmp_buf = None

    __header_ok = None
    __length = 0

    def init_func(self, creator, host, hostname="", conn_timeout=20, is_ipv6=False):
        """如果不是IPv4地址和IPv6地址,那么hostname就是host,否则使用hostname
        """
        self.__ssl_handshake_ok = False
        self.__hostname = host
        self.__update_time = time.time()
        self.__conn_timeout = conn_timeout
        self.__tmp_buf = []
        self.__header_ok = False
        self.__length = 0

        if netutils.is_ipv6_address(host):
            is_ipv6 = True
            self.__hostname = hostname
        if netutils.is_ipv4_address(host):
            is_ipv6 = False
            self.__hostname = hostname

        if is_ipv6:
            fa = socket.AF_INET6
        else:
            fa = socket.AF_INET

        s = socket.socket(fa, socket.SOCK_STREAM)
        s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)

        s = context.wrap_socket(s, do_handshake_on_connect=False, server_hostname=self.__hostname)

        context.verify_mode = ssl.CERT_REQUIRED
        context.load_verify_locations(self.dispatcher.ca_path)

        self.set_socket(s)
        self.__conn_timeout = conn_timeout

        server_ip = self.dispatcher.get_server_ip(host)
        if server_ip is None:
            logging.print_error("cannot get %s ip address" % host)
            s.close()
            return -1

        self.connect((server_ip, 853))

        return self.fileno

    def connect_ok(self):
        self.__update_time = time.time()
        self.set_timeout(self.fileno, self.__LOOP_TIMEOUT)
        self.register(self.fileno)
        self.add_evt_read(self.fileno)
        self.add_evt_write(self.fileno)

    def evt_read(self):
        if not self.is_conn_ok():
            super().evt_read()
            return

        if not self.__ssl_handshake_ok:
            self.do_ssl_handshake()

        if not self.__ssl_handshake_ok: return

        try:
            super().evt_read()
        except ssl.SSLWantWriteError:
            self.add_evt_write(self.fileno)
        except ssl.SSLWantReadError:
            if self.reader.size() > 0:
                self.tcp_readable()
        except ssl.SSLZeroReturnError:
            if self.reader.size() > 0:
                self.tcp_readable()
            if self.handler_exists(self.fileno): self.delete_handler(self.fileno)
        except ssl.SSLError:
            self.delete_handler(self.fileno)
        except:
            logging.print_error()
            self.delete_handler(self.fileno)

    def evt_write(self):
        if not self.is_conn_ok():
            super().evt_write()
            return

        if not self.__ssl_handshake_ok:
            self.remove_evt_write(self.fileno)
            self.do_ssl_handshake()

        if not self.__ssl_handshake_ok: return
        try:
            super().evt_write()
        except ssl.SSLWantReadError:
            pass
        except ssl.SSLWantWriteError:
            self.add_evt_write(self.fileno)
        except ssl.SSLEOFError:
            self.delete_handler(self.fileno)
        except ssl.SSLError:
            self.delete_handler(self.fileno)
        except:
            logging.print_error()
            self.delete_handler(self.fileno)

    def check_cert_is_expired(self):
        peer_cert = self.socket.getpeercert()
        expire_time = peer_cert["notAfter"]
        t = time.strptime(expire_time, "%b %d %H:%M:%S %Y %Z")
        expire_secs = time.mktime(t)
        now = time.time()

        if now > expire_secs: return True

        return False

    def flush_sent_buf(self):
        while 1:
            try:
                data = self.__tmp_buf.pop(0)
            except IndexError:
                break
            self.writer.write(data)
        self.add_evt_write(self.fileno)

    def do_ssl_handshake(self):
        try:
            self.socket.do_handshake()
            self.__ssl_handshake_ok = True
            cert = self.socket.getpeercert()
            if not hasattr(ssl, 'match_hostname'):
                ssl_backports.match_hostname(cert, self.__hostname)
            else:
                ssl.match_hostname(cert, self.__hostname)
            if self.check_cert_is_expired():
                logging.print_error("SSL handshake fail %s;certificate is expired" % self.__hostname)
                self.delete_handler(self.fileno)
                return
            self.add_evt_read(self.fileno)
            # 清空发送缓冲,发送数据
            self.flush_sent_buf()
        except ssl.SSLWantReadError:
            self.add_evt_read(self.fileno)
        except ssl.SSLWantWriteError:
            self.add_evt_write(self.fileno)
        except ssl.SSLZeroReturnError:
            self.delete_handler(self.fileno)
            logging.print_error("SSL handshake fail %s" % self.__hostname)
        except:
            logging.print_error()
            self.delete_handler(self.fileno)
        ''''''

    def parse_header(self):
        if not self.__header_ok and self.reader.size() < 2: return
        self.__length, = struct.unpack("!H", self.reader.read(2))
        self.__header_ok = True

    def tcp_readable(self):
        self.__update_time = time.time()
        if not self.__header_ok:
            self.parse_header()
        if not self.__header_ok: return
        if self.__length < self.reader.size(): return

        message = self.reader.read(self.__length)

        if len(message) >= 8:
            self.dispatcher.handle_msg_from_server(message)

        # 执行玩任务
        self.dispatcher.tell_conn_free(self.fileno)

    def tcp_writable(self):
        if self.writer.size() == 0: self.remove_evt_write(self.fileno)

    def tcp_delete(self):
        self.dispatcher.tell_conn_nonfree(self.fileno)
        self.__tmp_buf = []
        self.unregister(self.fileno)
        self.close()

    def tcp_error(self):
        logging.print_info("tcp_error %s" % self.__hostname)
        self.delete_handler(self.fileno)

    def tcp_timeout(self):
        if not self.is_conn_ok():
            logging.print_info("connecting_timeout  %s" % self.__hostname)
            self.delete_handler(self.fileno)
            return
        now = time.time()
        if now - self.__update_time >= self.__conn_timeout:
            self.delete_handler(self.fileno)

    def send_to_server(self, message: bytes):
        length = len(message)
        # 限制数据包大小
        if length > 1400: return
        if length < 8: return

        wrap_msg = struct.pack("!H", length) + message

        if not self.__ssl_handshake_ok:
            self.__tmp_buf.append(wrap_msg)
            return
        self.add_evt_write(self.fileno)
        self.writer.write(wrap_msg)
