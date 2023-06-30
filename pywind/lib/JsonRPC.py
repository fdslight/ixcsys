#!/usr/bin/env python3
# 实现一个json RPC

"""格式如下
version:4 byte ，固定版本为1
errcode:4 byte , 故障码,0表示未发生故障,否则表示发生错误
session_id:16 bytes,默认为全0,如果不需要认证
payload_length:8 bytes ,json负载长度
"""

import struct, json

VERSION = 1

class RPCErr(Exception):
    pass

class CallObject(object):
    __enable_auth = None

    __fn_tb = None

    def __init__(self):
        self.__enable_auth = False
        self.__fn_tb = {}

    def enable_auth(self, enable: bool):
        """启用或者关闭认证
        """
        self.__enable_auth = enable

    def handle_auth_reuqest(self, *args, **kwargs):
        """重写此方法
        """
        pass

    def reg_function(self, module_name: str, fn_name: str, fn: object):
        """注册函数
        """
        if module_name not in self.__fn_tb:
            self.__fn_tb[module_name] = {}

        o = self.__fn_tb[module_name]
        if fn_name in o:
            raise RPCErr("function %s exists at module %s" % (fn_name, module_name,))

        o[fn_name] = fn


class JsonRPC(object):
    __session_id = None
    __cb = None

    def __init__(self, module_name):
        self.__session_id = bytes(16)
        self.__cb = None

    def set_callback(self, fn: object):
        """设置回调函数,回调函数的参数个数为一个,并且类型为bytes
        """
        self.__cb = fn

    def request_auth(self, *args, **kwargs):
        return self.__build_request("auth", "auth", *args, *kwargs)

    def __build_request(self, module_name: str, fn_name: str, *args, **kwargs):
        o = {
            "module_name": module_name,
            "fn_name": fn_name,
            "args": args,
            "kwargs": kwargs
        }
        s = json.dumps(o)
        byte_data = s.encode()

        length = len(byte_data)

        rpc_request = struct.pack("!II16sQ", VERSION, 0, self.__session_id, length) + byte_data
        if self.__cb:
            self.__cb(rpc_request)
        else:
            return rpc_request

    def __fn_call(self,*args,**kwargs):
        pass

    def __getattr__(self, item):
        return self.__fn_call
