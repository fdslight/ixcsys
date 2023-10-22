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
            "forward_dns_result": self.forward_dns_result,
            "enable": self.enable,
            "get_nameservers": self.get_nameservers,
            "set_nameservers": self.set_nameservers,
            "is_auto": self.is_auto,
            "hosts_set": self.hosts_set,
            "hosts_save": self.hosts_save,
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

    def enable(self, enabled: bool, is_ipv6=False):
        """是否启用自动获取DNS或者关闭自动获取DNS
        """
        configs = self.__runtime.configs
        if is_ipv6:
            cfg = configs["ipv6"]
        else:
            cfg = configs["ipv4"]

        if enabled:
            cfg["enable_auto"] = 1
        else:
            cfg["enable_auto"] = 0
        return 0, None

    def forward_dns_result(self):
        """重定向DNS结果
        :return:
        """
        self.__runtime.forward_dns_result()
        return 0, None

    def save(self):
        self.__runtime.save_configs()
        return 0, None

    def get_nameservers(self, is_ipv6=False):
        """获取DNS服务器,该返回值会根据DNS的配置方式在运行期间变化
        :param is_ipv6:
        :return:
        """
        return 0, self.__runtime.get_nameservers(is_ipv6=is_ipv6)

    def set_nameservers(self, ns1: str, ns2: str, is_ipv6=False):
        if not self.__runtime.is_auto(): return 0, None
        return 0, self.__runtime.set_nameservers(ns1, ns2, is_ipv6=is_ipv6)

    def is_auto(self, is_ipv6=False):
        """是否为自动设置DNS地址
        """
        return 0, self.__runtime.is_auto(is_ipv6=is_ipv6)

    def hosts_set(self, host, addr, is_ipv6=False):
        return 0, self.__runtime.hosts_modify(host, addr, is_ipv6=is_ipv6)

    def hosts_save(self):
        self.__runtime.save_hosts()
        return 0, None
