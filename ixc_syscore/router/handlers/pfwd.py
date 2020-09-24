#!/usr/bin/env python3
"""数据包重定向
"""
import socket, struct, os
import pywind.evtframework.handlers.udp_handler as udp_handler

import ixc_syscore.router.pylib.router as router

HEADER_FMT = "!16sbbbb"


class pfwd(udp_handler.udp_handler):
    __sock_info = None

    # 链路层重定向表
    __link_fwd_tb = None
    # IP层重定向表
    __ip_fwd_tb = None

    __pkt_size = None

    def init_func(self, creator_fd):
        self.__link_fwd_tb = {
            router.IXC_FLAG_DHCP_CLIENT: None,
            router.IXC_FLAG_DHCP_SERVER: None,
        }

        self.__ip_fwd_tb = {

        }

        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.set_socket(s)
        self.bind(("127.0.0.1", 0))
        self.__sock_info = s.getsockname()

        self.register(self.fileno)
        self.add_evt_read(self.fileno)

        return self.fileno

    def udp_readable(self, message, address):
        """
        :param message:
        :param address:
        :return:
        """
        # 限制只能本机器进行通讯
        if address[0] != "127.0.0.1": return
        self.__pkt_size = len(message)
        if self.__pkt_size < 40: return

    def udp_writable(self):
        self.remove_evt_write(self.fileno)

    def udp_error(self):
        self.delete_handler(self.fileno)

    def udp_delete(self):
        self.unregister(self.fileno)
        self.close()

    def handle_link_from_netstack(self, if_type: int, flags: int, msg: bytes):
        fwd_info = self.__link_fwd_tb[flags]

        if not fwd_info: return

        new_msg = [
            struct.pack(HEADER_FMT, fwd_info[0], if_type, 0, 0, flags),
            msg
        ]
        self.sendto(b"".join(new_msg), ("127.0.0.1", fwd_info[1]))
        self.add_evt_write(self.fileno)

    def handle_ip_from_netstack(self, link_proto: int, ipproto: int, flags: int, msg: bytes):
        pass

    def recv_from_netstack(self, if_type: int, ipproto: int, flags: int, msg: bytes):
        """从协议栈接收数据
        :param if_type:
        :param ipproto:
        :param flags:
        :param msg:
        :return:
        """
        if not ipproto:
            self.handle_link_from_netstack(if_type, flags, msg)
        else:
            self.handle_ip_from_netstack(if_type, ipproto, flags, msg)

    def set_fwd_port(self, is_link_data: bool, flags: int, fwd_port: int):
        if fwd_port < 1 or fwd_port > 0xfffe:
            return (False, "wrong fwd_port value",)

        if is_link_data and flags not in self.__link_fwd_tb:
            return (False, "link data not have flags value %s" % flags,)

        if not is_link_data and flags not in self.__ip_fwd_tb:
            return (False, "ip data not have flags value %s" % flags,)

        if is_link_data:
            if self.__link_fwd_tb[flags]:
                return (False, "link data flags %s have been set" % flags,)
            self.__link_fwd_tb[flags] = (os.urandom(16), fwd_port,)
            return (True, self.__link_fwd_tb[flags][0],)

    def unset_fwd_port(self, is_link_data: bool, flags: int):
        if is_link_data:
            if flags not in self.__link_fwd_tb: return
            self.__link_fwd_tb[flags] = None

    def get_server_recv_port(self):
        return self.__sock_info[1]
