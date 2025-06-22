#!/usr/bin/env python3
"""与系统内部的C RPC进行通讯
"""

import socket, struct, time, pickle
import pywind.lib.reader as reader


class RPCError(Exception):
    pass


class RPCClient(object):
    __s = None
    __timeout = None
    __reader = None

    def __init__(self, path: str):
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

        self.__reader = reader.reader()
        self.__s = s
        self.__s.connect(path)
        self.__timeout = 3

    def send_rpc_request(self, func_name: str, arg_data: bytes):
        byte_fn_name = func_name.encode("iso-8859-1")

        if len(byte_fn_name) > 0xff:
            raise ValueError("wrong func name length,the size of max is 0xff")

        if len(arg_data) > 0xffff:
            raise ValueError("wrong arg_data length,the size of max is 0xffff")

        data = struct.pack("!H6s256s", len(arg_data) + 264, bytes(6), byte_fn_name)
        sent_data = b"".join([data, arg_data])

        while 1:
            if not sent_data: break
            try:
                sent_size = self.__s.send(sent_data)
            except:
                raise RPCError("rpc connection error from send")
            sent_data = sent_data[sent_size:]

    def fn_call(self, fname: str, *args, **kwargs):
        dic = {
            "args": args,
            "kwargs": kwargs
        }
        self.send_rpc_request(fname, pickle.dumps(dic))

        return self.recv_rpc_response()

    def set_timeout(self, timeout: int):
        self.__timeout = timeout

    def recv_rpc_response(self):
        """接收RPC响应
        """
        import traceback
        tot_len = 0
        begin = time.time()
        parsed_header = False

        is_error = 0
        msg = None

        while 1:
            now = time.time()
            if now - begin > self.__timeout:
                raise RPCError("response timeout")
            recv_data = self.__s.recv(4096)
            self.__reader._putvalue(recv_data)
            if self.__reader.size() < 16 and not parsed_header: continue
            if not parsed_header:
                tot_len, _, is_error = struct.unpack("!H6si", self.__reader.read(16))
                tot_len -= 16
                parsed_header = True
            if self.__reader.size() >= tot_len:
                msg = self.__reader.read(tot_len)
                break
            ''''''
        return is_error, msg

    def close(self):
        self.__s.close()

    def __del__(self):
        self.close()
