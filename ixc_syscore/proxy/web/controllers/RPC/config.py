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
            "dns_rule_update": self.dns_rule_update,
            "pass_ip_rule_update": self.pass_ip_rule_update,
            "proxy_ip_rule_update": self.proxy_ip_rule_update,
            "do_update": self.do_update
        }

    def config_get(self, cfg_type: str):
        if cfg_type not in ("dns", "pass-ip", "proxy-ip", "conn",):
            return RPC.ERR_ARGS, "wrong argument value %s" % cfg_type

        if cfg_type == "dns":
            return 0, {"rules": self.__runtime.proxy_domain_rule_raw_get}

        if cfg_type == "conn":
            return 0, self.__runtime.configs

        if cfg_type == "pass-ip":
            return 0, {"rules": self.__runtime.pass_ip_rule_raw_get}

        if cfg_type == "proxy-ip":
            return 0, {"rules": self.__runtime.proxy_ip_rule_raw_get}

        return 0, {}

    def dns_rule_update(self, text: str):
        self.__runtime.update_domain_rule(text)
        return 0, None

    def pass_ip_rule_update(self, text: str):
        self.__runtime.update_pass_ip_rule(text)
        return 0, None

    def proxy_ip_rule_update(self, text: str):
        self.__runtime.update_proxy_ip_rule(text)

        return 0, None

    def do_update(self):
        """执行更新动作,使规则立即生效
        :return:
        """
        return 0, None
