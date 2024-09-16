#!/usr/bin/env python3
import zlib, json

import ixc_syslib.web.controllers.rpc_controller as rpc
from pywind.global_vars import global_vars
import pywind.lib.netutils as netutils


class controller(rpc.controller):
    __runtime = None

    def rpc_init(self):
        self.__runtime = global_vars["ixcsys.secDNS"]

        self.fobjs = {
            "config_get": self.config_get,
            "dot_host_add": self.dot_host_add,
            "dot_host_del": self.dot_host_del,
            "dot_servers_get": self.dot_servers_get,
        }

    def config_get(self):
        return 0, self.__runtime.configs

    def dot_servers_get(self):
        return 0, self.__runtime.dot_configs

    def dot_host_add(self, host: str, hostname: str, comment: str):
        # 必须为IPv4地址或者IPv6地址
        if not netutils.is_ipv4_address(host) and not netutils.is_ipv6_address(host):
            return 0, None

        return 0, self.__runtime.dot_host_add(host, hostname, comment)

    def dot_host_del(self, host: str):
        return 0, self.__runtime.dot_host_del(host)
