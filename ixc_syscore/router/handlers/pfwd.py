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
    __fwd_tb = None
    __pkt_size = None

    def init_func(self, creator_fd):
        self.__fwd_tb = {
            router.IXC_FLAG_DHCP_CLIENT: None,
            router.IXC_FLAG_DHCP_SERVER: None,
            router.IXC_FLAG_ARP: None,
            router.IXC_FLAG_L2VPN: None,
            router.IXC_FLAG_SRC_FILTER: None,
            router.IXC_FLAG_ROUTE_FWD: None,
        }

        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.set_socket(s)
        self.bind(("127.0.0.1", 8964))
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
        if self.__pkt_size < 21: return

        _id, if_type, _, ipproto, flags = struct.unpack("!16sbbbb", message[0:20])

        if 0 != ipproto and self.__pkt_size < 41: return

        self.dispatcher.send_to_proto_stack(if_type, ipproto, flags, message[20:])

    def udp_writable(self):
        self.remove_evt_write(self.fileno)

    def udp_error(self):
        self.delete_handler(self.fileno)

    def udp_delete(self):
        self.unregister(self.fileno)
        self.close()

    def recv_from_netstack(self, if_type: int, ipproto: int, flags: int, msg: bytes):
        """从协议栈接收数据
        :param if_type:
        :param ipproto:
        :param flags:
        :param msg:
        :return:
        """
        if flags == router.IXC_FLAG_ARP:
            _list = [
                router.IXC_FLAG_ARP,
                router.IXC_FLAG_L2VPN,
                router.IXC_FLAG_DHCP_SERVER,
                router.IXC_FLAG_DHCP_CLIENT,
            ]
        else:
            _list = [flags]

        for i in _list:
            fwd_info = self.__fwd_tb[i]
            if not fwd_info: continue
            new_msg = [
                struct.pack(HEADER_FMT, fwd_info[0], if_type, 0, ipproto, flags),
                msg
            ]
            self.sendto(b"".join(new_msg), ("127.0.0.1", fwd_info[1]))
        self.add_evt_write(self.fileno)

    def set_fwd_port(self, flags: int, _id: bytes, fwd_port: int):
        if flags not in self.__fwd_tb: return False

        r = (_id, fwd_port,)
        self.__fwd_tb[flags] = r

        return True

    def unset_fwd_port(self, flags: int):
        if flags not in self.__fwd_tb: return
        self.__fwd_tb[flags] = None
