#!/usr/bin/env python3
"""实现DNS服务器代理,用于高级DNS过滤功能
"""
import socket, struct, os
import pywind.evtframework.handlers.udp_handler as udp_handler

import ixc_syslib.pylib.logging as logging
import ixc_syscore.tftp.pylib.tftp as tftplib


class context(object):
    """会话句柄
    """
    __fd = None
    __last_byte_data = None
    __block_no = 0
    __is_ack = None

    __rq_type = None
    __mode = None

    def __init__(self, fpath: str, rq_type: int, mode: str):
        self.__block_no = 0
        self.__rq_type = rq_type
        self.__mode = mode
        self.__fd = open(fpath, "rb")
        self.__last_byte_data = None
        self.__is_ack = False

    @property
    def rq_type(self):
        return self.__rq_type

    @property
    def fsize(self):
        return

    def get_block(self):
        """获取文件块
        :return tuple,(True|False,byte_data),True表示文件未结束,False表示文件已结束
        """
        if not self.__is_ack and self.__last_byte_data:
            return self.__last_byte_data

        fdata = self.__fd.read(512)
        size = len(fdata)

        self.__last_byte_data = fdata
        self.__block_no += 1
        self.__is_ack = False

        return size == 512, fdata

    def write(self, byte_data: bytes):
        pass

    def set_ack(self):
        """设置ACK
        """
        self.__is_ack = True

    def is_ack(self):
        """是否已经确认
        """
        return self.__is_ack

    def release(self):
        self.__fd.close()


class tftp(object):
    __file_dir = None
    __sessions = None
    __writable = None

    __runtime = None

    def __init__(self, runtime):
        configs = runtime.configs["conf"]

        self.__writable = bool(int(configs["enable_wrq"]))
        self.__runtime = runtime
        self.__file_dir = configs["file_dir"]
        self.__sessions = {}
        self.__readable = True
        self.__writable = False

    def set_tftp_mode(self, mode: int):
        """设置tftp的模式,模式可以是读或者写或者可读写
        """
        pass

    def send_error_msg(self, err_code: int, err_msg: str, client_addr: tuple):
        msg = tftplib.build_error(err_code, err_msg)
        self.__runtime.send_msg(msg, client_addr)

    def handle_rrq(self, request: tuple, client_addr: tuple):
        filename, mode = request
        if mode != "octet":
            self.send_error_msg(tftplib.ERR_NOT_DEF, "server only support octet mode", client_addr)
            return
        fpath = "%s/%s" % (self.__file_dir, filename,)

        if not os.path.isfile(fpath):
            self.send_error_msg(tftplib.ERR_FILE_NOT_FOUND, "not found file %s" % filename, client_addr)
            return
        session_id = "%s-%s" % client_addr

        if session_id in self.__sessions:
            self.send_error_msg(tftplib.ERR_NOT_DEF, "the session exists", client_addr)
            _context = self.__sessions[session_id]
            _context.release()
            return

        _context = context(fpath, tftplib.OP_RRQ, mode)

    def handle_wrq(self, request: tuple, client_addr: tuple):
        if not self.__writable: return

    def handle_data(self, block_no: int, byte_data: bytes):
        pass

    def handle_ack(self, block_no: int):
        pass

    def handle_error(self, errcode: int, errmsg: str):
        pass

    def handle_oack(self, options: dict):
        return

    def handle_tftp(self, byte_data: bytes, client_addr: tuple):
        session_id = "%s-%s" % client_addr

        try:
            rs = tftplib.parse(byte_data)
        except tftplib.TftpErr:
            logging.print_error()
            return

        rs = tftplib.parse(byte_data)
        opcode, obj = rs

        if (session_id not in self.__sessions) and (opcode not in (tftplib.OP_RRQ, tftplib.OP_WRQ,)):
            self.send_error_msg(tftplib.ERR_NOT_DEF, "not send WRQ or RRQ", client_addr)
            return
        if opcode == tftplib.OP_RRQ:
            self.handle_rrq(obj, client_addr)
            return
        if opcode == tftplib.OP_WRQ:
            self.handle_wrq(obj, client_addr)
            return
        if opcode == tftplib.OP_DATA:
            self.handle_data(*obj)
            return
        if opcode == tftplib.OP_ACK:
            self.handle_ack(obj)
            return
        if opcode == tftplib.OP_ERR:
            self.handle_error(*obj)
            return
        if opcode == tftplib.OP_OACK:
            self.handle_oack(obj)
            return


class tftpd(udp_handler.udp_handler):
    __is_ipv6 = None
    __tftp = None

    def init_func(self, creator_fd, bind_ip, is_ipv6=False):
        self.__is_ipv6 = is_ipv6
        self.__tftp = tftp(self)

        if is_ipv6:
            fa = socket.AF_INET6
        else:
            fa = socket.AF_INET

        s = socket.socket(fa, socket.SOCK_DGRAM)
        if is_ipv6: s.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
        self.set_socket(s)
        self.bind((bind_ip, 69))
        self.register(self.fileno)
        self.add_evt_read(self.fileno)

        return self.fileno

    def udp_readable(self, message, address):
        self.__tftp.handle_tftp(message, address)

    def udp_writable(self):
        self.remove_evt_write(self.fileno)

    def udp_error(self):
        pass

    def udp_delete(self):
        self.unregister(self.fileno)
        self.close()

    def udp_timeout(self):
        pass

    def send_msg(self, message: bytes, address: tuple):
        self.sendto(message, address)
        self.add_evt_write(self.fileno)

    @property
    def configs(self):
        return self.dispatcher.configs
