#!/usr/bin/env python3

import pickle
import pywind.lib.crpc as crpc
import ixc_syslib.web.controllers.rpc_controller as rpc
from pywind.global_vars import global_vars


class controller(rpc.controller):
    __runtime = None

    def rpc_init(self):
        self.__runtime = global_vars["ixcsys.runtime"]

        self.fobjs = {
        }

    def handle_rpc_request(self, fname: str, *args, **kwargs):
        client = crpc.RPCClient(self.__runtime.rpc_sock_path)
        is_error, msg = client.fn_call(fname, *args, **kwargs)

        self.send_rpc_response(is_error, pickle.loads(msg))
