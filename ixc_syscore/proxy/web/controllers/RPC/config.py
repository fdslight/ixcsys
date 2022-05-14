#!/usr/bin/env python3

from pywind.global_vars import global_vars

import ixc_syslib.web.controllers.rpc_controller as rpc
import ixc_syslib.pylib.RPCClient as RPC
import ixc_syscore.proxy.pylib.crypto.utils as crypto_utils


class controller(rpc.controller):
    __runtime = None

    def rpc_init(self):
        self.__runtime = global_vars["ixcsys.proxy"]

        self.fobjs = {
            "config_get": self.config_get,
            "dns_rule_update": self.dns_rule_update,
            "pass_ip_rule_update": self.pass_ip_rule_update,
            "proxy_ip_rule_update": self.proxy_ip_rule_update,
            "conn_cfg_update": self.conn_cfg_update,
            "get_crypto_modules": self.get_crypto_modules,
            "get_crypto_module_conf": self.get_crypto_module_conf,
            "update_crypto_module_conf": self.update_crypto_module_conf,

            "racs_cfg_update": self.racs_cfg_update,
        }

    def config_get(self, cfg_type: str):
        if cfg_type not in ("dns", "pass-ip", "proxy-ip", "conn", "racs",):
            return RPC.ERR_ARGS, "wrong argument value %s" % cfg_type

        if cfg_type == "dns":
            return 0, {"rules": self.__runtime.proxy_domain_rule_raw_get}

        if cfg_type in ("conn",):
            return 0, self.__runtime.configs

        if cfg_type == "pass-ip":
            return 0, {"rules": self.__runtime.pass_ip_rule_raw_get}

        if cfg_type == "proxy-ip":
            return 0, {"rules": self.__runtime.proxy_ip_rule_raw_get}

        if cfg_type == "racs":
            return 0, self.__runtime.racs_configs

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

    def conn_cfg_update(self, dic: dict):
        self.__runtime.conn_cfg_update(dic)
        return 0, None

    def get_crypto_modules(self):
        return 0, crypto_utils.get_crypto_modules()

    def get_crypto_module_conf(self, name: str):
        return 0, self.__runtime.get_crypto_module_conf(name)

    def update_crypto_module_conf(self, name: str, dic: dict):
        return 0, self.__runtime.save_crypto_module_conf(name, dic)

    def racs_cfg_update(self, cfg: dict):
        self.__runtime.racs_cfg_update(cfg)
        return 0, None
