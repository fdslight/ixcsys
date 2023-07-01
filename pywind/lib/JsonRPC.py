#!/usr/bin/env python3
# 实现一个json RPC

"""格式如下
version:4 byte ，固定版本为1
type:4 bytes 0表示ping,1表示pong,2表示RPC请求,3表示RPC响应
session_id:16 bytes,默认为全0,如果不需要认证
payload_length:4 bytes ,json负载长度
errcode:4 byte , 故障码,0表示未发生故障,否则表示发生错误

"""

import struct, json, socket, os, time

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


class _ModuleObject(object):
    __rpc_inst = None
    __module_name = None
    __func_name = None

    def __init__(self, rpc_inst, module_name):
        self.__rpc_inst = rpc_inst
        self.__module_name = module_name

    def __fn(self, *args, **kwargs):
        self.__rpc_inst.send_rpc_request("aaa", self.__module_name, self.__func_name, *args, **kwargs)

    def __getattr__(self, item):
        self.__func_name = item

        return self.__fn


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

    __root_module = None

    def __init__(self, *args, **kwargs):
        self.__reader = reader.reader()
        self.__rpc_functions = {}
        self.__session_id = bytes(16)
        self.__enable_auth = False
        self.__max_data_unit = MAX_DATA_UNIT_SIZE
        self.__heartbeat_time = 30
        self.__parse_header_ok = False
        self.__payload_length = 0
        self.__root_module = _ModuleObject(self, "root")

        self.reg_fn("root", "module_exists", self.__rpc_fn_module_exists)

        self.my_init(*args, **kwargs)

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

    def __build_request(self, module_name: str, fn_name: str, *args, **kwargs):
        o = {
            "id": "---",
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
        result = json_obj["result"]

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

        self.__handle_rpc_response(json_obj)

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

    def send_rpc_request(self, _id, module_name, fn_name, *args, **kwargs):
        frame = self.__build_request(module_name, fn_name, *args, **kwargs)
        print(frame)

    def parse_data(self, byte_data: bytes):
        self.__reader._putvalue(byte_data)

    def reg_fn(self, module_name: str, fn_name, f: object):
        if module_name not in self.__rpc_functions:
            self.__rpc_functions[module_name] = {}
        o = self.__rpc_functions[module_name]
        if fn_name in o:
            raise RPCErr("function %s exists at module %s" % (fn_name, module_name,))
        o[fn_name] = f

    def get_call_object(self, name: str, async_mode=False):
        if name == "root": return self.__root_module
        if async_mode: return _ModuleObject(self, name)

        if not self.__root_module.module_exists(name):
            raise RPCErr("not found module %s" % name)

        return _ModuleObject(self, name)


cls = JsonRPC()
obj = cls.get_call_object("test")
