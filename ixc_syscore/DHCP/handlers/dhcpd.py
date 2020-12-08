#!/usr/bin/env python3

import socket, struct
import pywind.evtframework.handlers.udp_handler as udp_handler


class dhcp_service(udp_handler.udp_handler):
    __sock_info = None
    __id = None
    __server_port = None

    __dhcp_server = None
    __dhcp_client = None

    @property
    def consts(self):
        return self.dispatcher.router_consts

    def init_func(self, creator_fd):
        self.__server_port = -1
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        self.set_socket(s)
        self.bind(("127.0.0.1", 0))
        self.__sock_info = s.getsockname()
        self.register(self.fileno)
        self.add_evt_read(self.fileno)

        return self.fileno

    def udp_readable(self, message, address):
        if address[0] != "127.0.0.1": return
        if address[1] != self.__server_port: return

        if len(message) < 34: return

        _id, if_type, _, ipproto, flags = struct.unpack("!16sbbbb", message[0:20])
        if _id != self.__id: return
        # 必须是链路层协议
        if ipproto != 0: return
        ether_data = message[20:]

        if flags == self.consts["IXC_FLAG_ARP"]:
            self.dispatcher.handle_arp_data(ether_data)
            return

        if if_type == self.consts["IXC_NETIF_LAN"] and flags == self.consts["IXC_FLAG_DHCP_SERVER"]:
            if self.dispatcher.dhcp_server_enable: self.dispatcher.server.handle_dhcp_msg(ether_data)
            return

        if if_type == self.consts["IXC_NETIF_WAN"] and flags == self.consts["IXC_FLAG_DHCP_CLIENT"]:
            if self.dispatcher.dhcp_client_enable: self.dispatcher.client.handle_dhcp_msg(ether_data)
            return

    def udp_writable(self):
        self.remove_evt_write(self.fileno)

    def udp_error(self):
        self.delete_handler(self.fileno)

    def udp_delete(self):
        self.unregister(self.fileno)
        self.close()

    def get_sock_port(self):
        return self.__sock_info[1]

    def set_message_auth(self, _id: bytes):
        """设置消息认证
        :param _id:
        :return:
        """
        self.__id = _id
        self.__server_port = 8964

    def send_dhcp_msg(self, if_type: int, flags: int, message: bytes):
        header = struct.pack("!16sbbbb", self.__id, if_type, 0, 0, flags)
        sent_msg = b"".join([header, message])

        self.add_evt_write(self.fileno)
        self.sendto(sent_msg, ("127.0.0.1", self.__server_port))
