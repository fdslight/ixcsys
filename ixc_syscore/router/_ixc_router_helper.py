#!/usr/bin/env python3
import pickle

import router

import ixc_syslib.pylib.logging as logging
import ixc_syscore.router.pylib.pppoe as pppoe

import pywind.lib.netutils as netutils


class rpc(object):
    __fn_objects = None

    def __init__(self, _helper):
        self.__fn_objects = {
            "netif_set_ip": None,
            "netif_get_ip": None,
            "route_add": self.route_add,
            "route_del": None,

        }

    def route_add(self):
        return

    def call(self, fn_name: str, *args, **kwargs):
        """调用函数
        """
        if fn_name not in self.__fn_objects:
            return 0, pickle.dumps("not found function %s" % fn_name)

        fn = self.__fn_objects[fn_name]

        return fn(*args, **kwargs)


class helper(object):
    __router = None
    __debug = None

    __WAN_BR_NAME = None
    __LAN_BR_NAME = None

    __LAN_NAME = None
    __WAN_NAME = None

    __pppoe = None
    __pppoe_enable = None
    __pppoe_user = None
    __pppoe_passwd = None

    def __init__(self):
        self.__router = router.router()

    @property
    def router(self):
        return self.__router

    def pppoe_session_handle(self, protocol: int, byte_data: bytes):
        """处理来自于C语言的PPPoE绘画数据
        """
        pass

    @property
    def pppoe_user(self):
        return self.__pppoe_user

    @property
    def pppoe_passwd(self):
        return self.__pppoe_passwd

    def rpc_fn_call(self, name: str, arg_data: bytes):
        """C程序调佣此函数执行RPC
        :return (is_error,byte_message)
        """
        return 0, b""

    def tell(self, cmd: str, *args):
        """C程序对Python的信号告知
        """
        pass

    def loop(self):
        """C程序调用此函数以便执行定时任务
        """
        pass
