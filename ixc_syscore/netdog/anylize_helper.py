#!/usr/bin/env python3

import sys, os, signal, json, time, struct

sys.path.append(os.getenv("IXC_SYS_DIR"))

if not os.path.isdir(os.getenv("IXC_MYAPP_TMP_DIR")): os.mkdir(os.getenv("IXC_MYAPP_TMP_DIR"))

import netpkt_anylize

import ixc_syslib.pylib.logging as logging
import ixc_syslib.pylib.RPCClient as RPCClient


class helper(object):
    __npkt_anylize = None
    __debug = None
    __consts = None

    __msg_flags = None

    def __init__(self, debug: bool):
        self.__debug = debug
        self.__npkt_anylize = netpkt_anylize.npkt_anylize()

        RPCClient.wait_processes(["router"])

    def start(self):
        key, port = self.__npkt_anylize.message_id_with_router_get()
        work_no = self.__npkt_anylize.worker_no_get()
        self.__consts = RPCClient.fn_call("router", "/config", "get_all_consts")

        flags = int(self.__consts['IXC_FLAG_TRAFFIC_COPY_MIN']) + work_no
        self.__msg_flags = flags

        RPCClient.fn_call("router", "/config", "unset_fwd_port", flags)
        key, port = RPCClient.fn_call("router", "/config", "set_fwd_port", flags,
                                      key, port)

    def loop(self):
        pass

    def release(self):
        RPCClient.fn_call("router", "/config", "unset_fwd_port", self.__msg_flags)
