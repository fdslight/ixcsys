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

            "racs_enable": self.racs_enable,
            "racs_host_set": self.racs_host_set,
            "racs_security_set": self.racs_security_set,
            "racs_network_route_set": self.racs_network_route_set,
            "racs_network_ip6_enable": self.racs_network_ip6_enable,
            "racs_save": self.racs_save,
        }

    @property
    def proxy(self):
        g = global_vars["ixcsys.proxy"]
        return g

    def config_get(self, cfg_type: str):
        if cfg_type not in ("dns", "pass-ip", "proxy-ip", "conn",):
            return RPC.ERR_ARGS, "wrong argument value %s" % cfg_type

        if cfg_type == "dns":
            return 0, {"rules": self.__runtime.proxy_domain_rule_raw_get}

        if cfg_type in ("conn",):
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

    def conn_cfg_update(self, dic: dict):
        self.__runtime.conn_cfg_update(dic)
        return 0, None

    def get_crypto_modules(self):
        return 0, crypto_utils.get_crypto_modules()

    def get_crypto_module_conf(self, name: str):
        return 0, self.__runtime.get_crypto_module_conf(name)

    def update_crypto_module_conf(self, name: str, dic: dict):
        return 0, self.__runtime.save_crypto_module_conf(name, dic)

    def racs_enable(self, enable: bool):
        configs = self.proxy.racs_configs
        conn = configs["connection"]
        conn["enable"] = enable

    def racs_host_set(self, host, port, enable_ipv6=False):
        configs = self.proxy.racs_configs
        conn = configs["connection"]
        conn["host"] = host
        conn["port"] = port
        conn["enable_ip6"] = enable_ipv6

    def racs_security_set(self, shared_key: str, priv_key: str):
        configs = self.proxy.racs_configs
        sec = configs["security"]
        sec["shared_key"] = shared_key
        sec["private_key"] = priv_key

    def racs_network_route_set(self, subnet, prefix, is_ipv6=False):
        configs = self.proxy.racs_configs
        network = configs["network"]

        if is_ipv6:
            network["ip6_route"] = "%s/%s" % (subnet, prefix,)
        else:
            network["ip_route"] = "%s/%s" % (subnet, prefix,)

    def racs_network_ip6_enable(self, enabled: bool):
        configs = self.proxy.racs_configs
        network = configs["network"]
        network["enable_ip6"] = enabled

    def racs_save(self):
        self.proxy.save_racs_configs()
