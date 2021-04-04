#!/usr/bin/env python3

import pickle

import pywind.lib.crpc as crpc
import ixc_syslib.web.controllers.rpc_controller as rpc
import ixc_syslib.pylib.RPCClient as RPCClient
from pywind.global_vars import global_vars


class controller(rpc.controller):
    __runtime = None

    def rpc_init(self):
        self.__runtime = global_vars["ixcsys.runtime"]

        self.fobjs = {
        }

    def handle_rpc_request(self, fname: str, *args, **kwargs):
        client = crpc.RPCClient(self.__runtime.rpc_sock_path)

        dic = {
            "args": args,
            "kwargs": kwargs
        }

        try:
            is_error, msg = client.send_rpc_request(fname, pickle.dumps(dic))
        except crpc.RPCError:
            self.send_rpc_response(RPCClient.ERR_SYS, "system error for function %s" % fname)
            return
        self.send_rpc_response(is_error, msg)
