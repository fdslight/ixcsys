#!/usr/bin/env python3
"""实现DNS服务器代理,用于高级DNS过滤功能
"""
import socket, struct, os, time
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

    __client_addr = None
    __up_time = None
    __tftp_obj = None

    __is_finished = None

    def __init__(self, tftp_obj, fpath: str, rq_type: int, mode: str, client_addr: tuple):
        self.__tftp_obj = tftp_obj
        self.__block_no = 1
        self.__rq_type = rq_type
        self.__mode = mode
        self.__last_byte_data = None
        self.__is_ack = False

        if rq_type == tftplib.OP_RRQ:
            self.__fd = open(fpath, "rb")
        else:
            self.__fd = open(fpath, "wb")
        self.__client_addr = client_addr
        self.__up_time = time.time()
        self.__is_finished = False

    @property
    def rq_type(self):
        return self.__rq_type

    @property
    def fsize(self):
        return

    @property
    def client_addr(self):
        return self.__client_addr

    def block_no_plus(self):
        """块号加1
        """
        if self.__block_no == 0xffff:
            self.__block_no = 0
        else:
            self.__block_no += 1
        return self.__block_no

    def get_block(self):
        """获取文件块
        :return tuple,(True|False,byte_data),True表示文件未结束,False表示文件已结束
        """
        t = time.time() - self.__up_time
        if not self.__is_ack and self.__last_byte_data:
            # 小于1s步伐送数据包
            if t < 1: return None
            return len(self.__last_byte_data) == tftplib.BLK_SIZE, self.__block_no, self.__last_byte_data

        if self.__is_finished: return None

        fdata = self.__fd.read(tftplib.BLK_SIZE)
        size = len(fdata)

        self.__last_byte_data = fdata
        self.__is_ack = False
        self.__is_finished = size != tftplib.BLK_SIZE

        return self.__is_finished, self.__block_no, fdata

    def write(self, block_no: int, byte_data: bytes):
        """写入数据
        :param block_no
        :param byte_data
        :return Boolean,True表示写入成功,False表示block_no错误
        """
        if block_no == self.__block_no:
            self.__fd.seek(self.__block_no * tftplib.BLK_SIZE)
            self.__fd.write(byte_data)
            return True
        if block_no != self.block_no_plus():
            return False

        self.__fd.seek(self.__block_no * tftplib.BLK_SIZE)
        self.__fd.write(byte_data)

    def set_ack(self, ack_no: int):
        """设置ACK
        :return Boolean,True表示成功,False表示序列号错误
        """
        if ack_no != self.__block_no: return
        self.__up_time = time.time()
        self.__is_ack = True
        self.block_no_plus()

    def is_finished(self):
        t = time.time() - self.__up_time
        # 超时5s那么默认认为结束
        if t > 5: return True
        return self.__is_finished and self.__is_ack

    def is_ack(self):
        """是否已经确认
        """
        return self.__is_ack

    def do_read(self):
        rs = self.get_block()
        if not rs: return
        have_content, block_no, byte_data = rs
        self.__tftp_obj.send_data_msg(block_no, byte_data, self.__client_addr)

        return self.is_finished()

    def do(self):
        rs = self.do_read()
        return rs

    def release(self):
        self.__fd.close()


class tftp(object):
    __file_dir = None
    __runtime = None
    __is_wrq = None

    def __init__(self, runtime):
        configs = runtime.configs["conf"]

        self.__runtime = runtime
        self.__file_dir = configs["file_dir"]
        self.__readable = True
        # 是否是写请求
        self.__is_wrq = False

    @property
    def sessions(self):
        return self.__runtime.sessions

    def send_error_msg(self, err_code: int, err_msg: str, client_addr: tuple):
        msg = tftplib.build_error(err_code, err_msg)
        self.__runtime.send_msg(msg, client_addr)

    def send_ack(self, block_no: int, client_addr: tuple):
        msg = tftplib.build_ack(block_no)
        self.__runtime.send_msg(msg, client_addr)

    def send_data_msg(self, block_no: int, byte_data: bytes, client_addr: tuple):
        msg = tftplib.build_data(block_no, byte_data)
        self.__runtime.send_msg(msg, client_addr)

    def handle_rrq(self, request: tuple, client_addr: tuple):
        filename, mode = request
        fpath = "%s/%s" % (self.__file_dir, filename,)

        if not os.path.isfile(fpath):
            self.send_error_msg(tftplib.ERR_FILE_NOT_FOUND, "not found file %s" % filename, client_addr)
            return
        session_id = "%s-%s" % client_addr

        if session_id in self.sessions:
            self.send_error_msg(tftplib.ERR_NOT_DEF, "the session exists", client_addr)
            _context = self.sessions[session_id]
            _context.release()
            return

        logging.print_info("send tftp file %s to client %s" % (fpath, client_addr[0],))

        _context = context(self, fpath, tftplib.OP_RRQ, mode, client_addr)
        self.sessions[session_id] = _context

    def handle_data(self, block_no: int, byte_data: bytes, _context):
        pass

    def handle_ack(self, block_no: int, _context):
        _context.set_ack(block_no)
        _context.do()
        return _context.is_finished()

    def handle_error(self, errcode: int, errmsg: str, _context):
        pass

    def handle_oack(self, options: dict, session_id: str):
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

        if opcode == tftplib.OP_WRQ:
            self.send_error_msg(tftplib.ERR_OP, "server cannot support WRQ", client_addr)
            return

        if opcode == tftplib.OP_RRQ and (session_id not in self.sessions):
            self.handle_rrq(obj, client_addr)
            return

        if session_id not in self.sessions:
            self.send_error_msg(tftplib.ERR_ID, "not send RRQ or WRQ request", client_addr)
            return

        _context = self.sessions[session_id]

        if opcode == tftplib.OP_DATA:
            self.handle_data(*obj)
            return

        if opcode == tftplib.OP_ACK:
            is_finished = self.handle_ack(obj, _context)
            if is_finished:
                _context.release()
                del self.sessions[session_id]
            return

        if opcode == tftplib.OP_ERR:
            self.handle_error(*obj, _context)
            return

        if opcode == tftplib.OP_OACK:
            self.handle_oack(obj, _context)
            return
        return

    def loop(self):
        dels = []
        for _id in self.sessions:
            _context = self.sessions[_id]
            is_finished = _context.do()
            if is_finished: dels.append(_id)
        for _id in dels: del self.sessions[_id]


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

    @property
    def sessions(self):
        return self.dispatcher.sessions

    def loop(self):
        self.__tftp.loop()
