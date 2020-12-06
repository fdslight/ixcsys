#!/usr/bin/env python3

import ixc_syslib.web.controllers.rpc_controller as rpc

import ixc_syslib.pylib.RPCClient as RPC

from pywind.global_vars import global_vars
import pywind.lib.netutils as netutils


class controller(rpc.controller):
    __runtime = None

    def rpc_init(self):
        self.__runtime = global_vars["ixcsys.DNS"]

        self.fobjs = {
            "config_get": self.config_get,
            "set_parent_server": self.set_parent_server,
            "enable": self.enable,
            "save": self.save
        }

    def config_get(self):
        return 0, self.__runtime.configs

    def set_parent_server(self, server_ip, is_main_server=False, is_ipv6=False):
        """设置上游服务器IP地址
        """
        if is_ipv6 and not netutils.is_ipv6_address(server_ip):
            return RPC.ERR_ARGS, "Wrong IPv6 address format"
        if not is_ipv6 and not netutils.is_ipv4_address(server_ip):
            return RPC.ERR_ARGS, "Wrong IP address format"

        configs = self.__runtime.configs
        if is_ipv6:
            if is_main_server:
                configs["ipv6"]["main_dns"] = server_ip
            else:
                configs["ipv6"]["second_dns"] = server_ip
            ''''''
        else:
            if is_main_server:
                configs["ipv4"]["main_dns"] = server_ip
            else:
                configs["ipv4"]["second_dns"] = server_ip
            ''''''
        return 0, None

    def enable(self, enabled: bool):
        """是否启用自动获取DNS或者关闭自动获取DNS
        """
        configs = self.__runtime.configs
        if enabled:
            configs["public"]["enable_auto"] = 1
        else:
            configs["public"]["enable_auto"] = 0
        return 0, None

    def save(self):
        self.__runtime.save_configs()
        return 0, None
