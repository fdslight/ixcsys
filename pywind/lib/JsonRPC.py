#!/usr/bin/env python3
# 实现一个json RPC

"""格式如下
version:4 byte ，固定版本为1
type:4 bytes 0表示ping,1表示pong,2表示RPC请求,3表示RPC响应
session_id:16 bytes,默认为全0,如果不需要认证
payload_length:4 bytes ,json负载长度
errcode:4 byte , 故障码,0表示未发生故障,否则表示发生错误

"""

import struct, json, socket, os, time, random

import pywind.lib.reader as reader

VERSION = 1
HEADER_SIZE = 32
HEADER_FMT = "!II16sII"

MAX_DATA_UNIT_SIZE = 8192

RPC_PING = 0
RPC_PONG = 1
RPC_REQ = 2
RPC_RESP = 3

RPC_CODES = (
    RPC_PING, RPC_PONG,
    RPC_REQ, RPC_RESP,
)


class RPCErr(Exception):
    pass


class JsonRPC(object):
    __reader = None

    __rpc_functions = None
    __session_id = None
    __enable_auth = None

    # 最大数据传输大小
    __max_data_unit = None

    __heartbeat_time = None

    __parse_header_ok = None
    __payload_length = None
    __errcode = None
    __type = None

    __call_ids = None

    __async_mode = None

    def __init__(self, *args, **kwargs):
        self.__reader = reader.reader()
        self.__rpc_functions = {}
        self.__session_id = bytes(16)
        self.__enable_auth = False
        self.__max_data_unit = MAX_DATA_UNIT_SIZE
        self.__heartbeat_time = 30
        self.__parse_header_ok = False
        self.__payload_length = 0
        self.__call_ids = {}
        self.__async_mode = False

        self.my_init(*args, **kwargs)

    def __rand_string(self, size=32):
        s = "1234567890QWERTYUIOPASDFGHJKLZXCVBNMqwertyuiopasdfghjklzxcvbnm"
        max_v = len(s) - 1
        results = []

        for i in range(size):
            n = random.randint(0, max_v)
            results.append(s[n])

        return "".join(results)

    def __gen_id(self):
        is_ok = False
        for i in range(10):
            _id = self.__rand_string()
            if _id in self.__call_ids: continue
            is_ok = True
            break

        if not is_ok:
            raise RPCErr("cannot generate RPC request id")

        return _id

    def my_init(self, *args, **kwargs):
        """重写这个方法
        """
        pass

    def wrap_frame_for_send(self, frame: bytes):
        """装饰RPC要发送的数据帧,重写这个方法
        """
        print(frame)

    def __build_data_frame(self, _type: int, errcode: int, message: bytes):
        if _type not in RPC_CODES:
            raise RPCErr("wrong RPC frame type %s" % _type)
        length = len(message)
        frame = struct.pack(HEADER_FMT, VERSION, _type, self.__session_id, length, errcode) + message

        return frame

    def __build_request(self, _id, module_name: str, fn_name: str, *args, **kwargs):
        o = {
            "id": _id,
            "module_name": module_name,
            "fn_name": fn_name,
            "args": args,
            "kwargs": kwargs,
        }
        s = json.dumps(o)
        frame = self.__build_data_frame(RPC_REQ, 0, s.encode())

        return frame

    def __send_rpc_response(self, _id, result, is_error=False):
        o = {
            "id": _id,
            "is_error": is_error,
            "result": result
        }

        self.__send(RPC_RESP, 0, json.dumps(o).encode())

    def __handle_rpc_request(self, json_obj: object):
        _id = json_obj["id"]
        module_name = json_obj["module_name"]
        fn_name = json_obj["fn_name"]

        if module_name not in self.__rpc_functions:
            s = "module %s not found" % module_name
            self.__send_rpc_response(_id, s, is_error=True)
            return

        o = json_obj[module_name]
        if fn_name not in o:
            s = "function %s not found from module" % (fn_name, module_name,)
            self.__send_rpc_response(_id, s, is_error=True)
            return

        fn = o[fn_name]

        try:
            return_value = fn(*json_obj["args"], **json_obj["kwargs"])
        except:
            return

        self.__send_rpc_response(_id, return_value, is_error=False)

    def __handle_rpc_response(self, json_obj: object):
        _id = json_obj["id"]

        if _id not in self.__call_ids: return

        result = json_obj["result"]
        is_error = json_obj["is_error"]

        if is_error:
            raise RPCErr(result)

        o = self.__call_ids[_id]

        if o["type"] == "sync": return True, result

        return False, None

    def __rpc_fn_module_exists(self, _id, module_name: str):
        return False, True

    def set_max_data_unit(self, max_size: int):
        if max_size < MAX_DATA_UNIT_SIZE:
            raise RPCErr("max data unit value is 8192 at least")
        self.__max_data_unit = max_size

    def set_heartbeat_time(self, seconds: int):
        if seconds < 10:
            raise RPCErr("heartbeat time is 10 at least")

        self.__heartbeat_time = seconds

    def __parse_header(self):
        if self.__reader.size() < HEADER_SIZE: return
        ver, _type, session_id, payload_length, errcode = struct.unpack(HEADER_FMT, self.__reader.read(HEADER_SIZE))

        if _type not in RPC_CODES:
            raise RPCErr("wrong RPC frame type %s" % _type)

        if payload_length > self.__max_data_unit:
            raise RPCErr("RPC peer frame is too long,the size of is %s" % payload_length)

        self.__type = _type

        self.__errcode = errcode
        self.__parse_header_ok = True
        self.__payload_length = payload_length

    def __send_pong(self):
        self.__send(RPC_PONG, 0, os.urandom(16))

    def __send_ping(self):
        frame = self.__send(RPC_PING, 0, os.urandom(16))

    def __send(self, _type: int, errcode: int, message: bytes):
        frame = self.__build_data_frame(_type, errcode, message)
        self.wrap_frame_for_send(frame)

    def __parse_body(self):
        if self.__reader.size() < self.__payload_length: return

        self.__parse_header_ok = False
        byte_data = self.__reader.read(self.__payload_length)

        if self.__type == RPC_PING:
            self.__send_pong()
            return

        if self.__type == RPC_PONG:
            return

        s = byte_data.decode()

        if self.__errcode != 0:
            raise RPCErr(s)

        try:
            json_obj = json.loads(s)
        except:
            raise RPCErr("peer send wrong data frame")

        if self.__type == RPC_REQ:
            if not self.__check_rpc_request_format(json_obj):
                raise RPCErr("wrong RPC request format")
            self.__handle_rpc_request(json_obj)
            return

        if not self.__check_rpc_response_format(json_obj):
            raise RPCErr("wrong RPC response format")

        return self.__handle_rpc_response(json_obj)

    def __check_rpc_request_format(self, o: object):
        if not isinstance(o, dict):
            return False

        keys = ("id", "module_name", "fn_name", "args", "kwargs",)
        for k, v in o.items():
            if k not in keys:
                return False
            if k == "args" and not isinstance(v, list):
                return False

            if k == "kwargs" and not isinstance(v, dict):
                return False
            ''''''
        return True

    def __check_rpc_response_format(self, o: object):
        if not isinstance(o, dict):
            return False

        keys = ("id", "result", "is_error",)

        for k, v in o.items():
            if k not in keys:
                return False
            ''''''
        return True

    def send_rpc_request(self, module_name, fn_name, *args, **kwargs):
        # 同步模式下ID可以不做要求
        _id = self.__gen_id()
        self.__call_ids[_id] = {"type": "sync", "args": None, "kwargs": None, "fn": None}
        frame = self.__build_request(_id, module_name, fn_name, *args, **kwargs)

        self.wrap_frame_for_send(frame)
        result = self.handle_peer_message()

        return result

    def async_send_rpc_request(self, module_name, fn_name, cb, cb_args, cb_kwargs, *args, **kwargs):
        _id = self.__gen_id()
        self.__call_ids[_id] = {"type": "async", "args": cb_args, "kwargs": cb_kwargs, "fn": cb}
        frame = self.__build_request(_id, module_name, fn_name, *args, **kwargs)

        self.wrap_frame_for_send(frame)

    def parse_data(self, byte_data: bytes):
        self.__reader._putvalue(byte_data)

        while 1:
            if not self.__parse_header_ok and self.__reader.size() < HEADER_SIZE: break
            if not self.__parse_header_ok:
                self.__parse_header()
            if not self.__parse_header_ok: break
            if self.__payload_length < self.__reader.size(): break
            rs = self.__parse_body()
            if not rs: continue
            is_sync, result = rs
            if is_sync:
                return result

    def set_async_mode(self, enable: bool):
        """设置是否作为异步模式
        """
        self.__async_mode = enable

    def handle_peer_message(self):
        """获取对端消息,重写这个方法,函数返回RPC结果
        """
        byte_data = b""
        return self.parse_data(byte_data)

    def reg_fn(self, module_name: str, fn_name, f: object):
        if module_name not in self.__rpc_functions:
            self.__rpc_functions[module_name] = {}
        o = self.__rpc_functions[module_name]
        if fn_name in o:
            raise RPCErr("function %s exists at module %s" % (fn_name, module_name,))
        o[fn_name] = f

    def call_fn(self, module_name, fn_name, *args, **kwargs):
        if self.__async_mode:
            raise RPCErr("async mode cannot call remote funciton by this function")
        result = self.send_rpc_request(module_name, fn_name, *args, **kwargs)

        return result

    def async_call_fn(self, module_name, fn_name, cb, cb_args, cb_kwargs, *args, **kwargs):
        if not self.__async_mode:
            raise RPCErr("sync mode cannot call remote funciton by this function")
        self.async_send_rpc_request(module_name, fn_name, cb, cb_args, cb_kwargs, *args, **kwargs)
