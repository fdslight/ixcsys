#!/usr/bin/env python3

import ixc_syslib.web.controllers.rpc_controller as rpc

import ixc_syslib.pylib.RPCClient as RPC

from pywind.global_vars import global_vars
import pywind.lib.netutils as netutils


class controller(rpc.controller):
    __runtime = None

    def rpc_init(self):
        self.__runtime = global_vars["ixcsys.proxy"]

        self.fobjs = {
            "config_get": self.config_get,
            "save": self.save
        }

    def config_get(self, cfg_type: str):
        if cfg_type not in ("dns", "pass-ip", "proxy-ip", "conn",):
            return RPC.ERR_ARGS, "wrong argument value %s" % cfg_type

        if cfg_type == "dns":
            return 0, {"rules":self.__runtime.proxy_domain_rule_raw_get}

        if cfg_type == "conn":
            return 0, self.__runtime.configs

        if cfg_type == "pass-ip":
            return 0, {"rules":self.__runtime.pass_ip_rule_raw_get}

        if cfg_type == "proxy-ip":
            return 0, {"rules":self.__runtime.proxy_ip_rule_raw_get}

        return 0, {}

    def save(self):
        return 0, None
