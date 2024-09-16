#!/usr/bin/env python3
"""客户端隧道实现
"""

import socket, time, ssl
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
    __id = None

    def init_func(self, creator, _id, host, hostname="", conn_timeout=30, is_ipv6=False):
        """如果不是IPv4地址和IPv6地址,那么hostname就是host,否则使用hostname
        """
        self.__id = _id
        self.__ssl_handshake_ok = False
        self.__hostname = host
        self.__update_time = time.time()
        self.__conn_timeout = conn_timeout

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

        logging.print_info("connected dot server %s" % self.__hostname)

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
            logging.print_info("dot tls handshake ok %s" % self.__hostname)
            self.add_evt_read(self.fileno)
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

    def tcp_readable(self):
        rdata = self.reader.read()
        self.__update_time = time.time()
        return

    def tcp_writable(self):
        if self.writer.size() == 0: self.remove_evt_write(self.fileno)

    def tcp_delete(self):
        self.dispatcher.tunnel_conn_fail()
        self.unregister(self.fileno)
        self.close()

        if self.is_conn_ok():
            logging.print_info("disconnect %s" % self.__hostname)
        return

    def tcp_error(self):
        logging.print_info("tcp_error %s" % self.__hostname)
        self.delete_handler(self.fileno)

    def tcp_timeout(self):
        if not self.is_conn_ok():
            self.dispatcher.tunnel_conn_fail()
            logging.print_error("connecting_timeout  %s" % self.__hostname)
            self.delete_handler(self.fileno)
            return

        t = time.time()
        v = t - self.__update_time

        if v > self.__conn_timeout:
            self.delete_handler(self.fileno)
            logging.print_info("connected_timeout %s" % self.__hostname)
            return

        self.set_timeout(self.fileno, 10)

    def send_to_server(self, message: bytes):
        pass
