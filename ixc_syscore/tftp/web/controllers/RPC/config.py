#!/usr/bin/env python3

import ixc_syslib.web.controllers.rpc_controller as rpc

from pywind.global_vars import global_vars

import ixc_syslib.pylib.RPCClient as RPC


class controller(rpc.controller):
    __runtime = None

    def rpc_init(self):
        self.__runtime = global_vars["ixcsys.tftp"]

        self.fobjs = {
            "config_get": self.config_get,
            "config_write": self.config_write,
        }

    def config_get(self):
        return 0, self.__runtime.configs["conf"]

    def config_write(self, configs: dict):
        keys = [
            "enable_ipv6", "file_dir",
        ]
        if not isinstance(configs, dict):
            return RPC.RPCArgErr, "Wrong Argument Type"

        for name in configs:
            if name not in keys: return RPC.RPCArgErr, "unkown key %s" % name

        x = self.__runtime.configs["conf"]
        for name, value in configs.items(): x[name] = value
        self.__runtime.save_configs()

        return 0, None
