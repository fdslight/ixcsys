#!/usr/bin/env python3
import zlib, json

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
            "set_ip6_nameservers_from_dhcpv6": self.set_ip6_nameservers_from_dhcpv6,
            "is_auto": self.is_auto,
            "hosts_set": self.hosts_set,
            "hosts_save": self.hosts_save,
            "hosts_get": self.hosts_get,
            "set_dnsv6_drop_enable": self.set_dnsv6_drop_enable,
            "dns_no_system_drop_enable": self.dns_no_system_drop_enable,
            "no_proxy_ips_add": self.no_proxy_ips_add,
            "save": self.save,
            "enable_sec_dns": self.enable_sec_dns,
            "is_enabled_sec_dns": self.is_enabled_sec_dns,
            "set_sec_dns_forward": self.set_sec_dns_forward,
            "add_sec_dns_domains": self.add_sec_dns_domains,
            "del_sec_dns_domains": self.del_sec_dns_domains,
            "set_dns_cache_timeout":self.set_dns_cache_timeout,
            "clear_dns_cache":self.clear_dns_cache,
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

    def forward_dns_result(self, enable: bool):
        """重定向DNS结果
        :return:
        """
        self.__runtime.forward_dns_result(enable)
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

    def set_ip6_nameservers_from_dhcpv6(self, ns1: str, ns2: str):
        return 0, self.__runtime.set_ip6_nameservers_from_dhcpv6(ns1, ns2)

    def is_auto(self, is_ipv6=False):
        """是否为自动设置DNS地址
        """
        return 0, self.__runtime.is_auto(is_ipv6=is_ipv6)

    def hosts_set(self, host, addr, is_ipv6=False):
        return 0, self.__runtime.hosts_modify(host, addr, is_ipv6=is_ipv6)

    def hosts_get(self):
        return 0, self.__runtime.hosts

    def hosts_save(self):
        self.__runtime.save_hosts()
        return 0, None

    def set_dnsv6_drop_enable(self, enable: bool):
        self.__runtime.set_drop_dnsv6_enable(enable)

        return 0, None

    def dns_no_system_drop_enable(self, enable: bool):
        self.__runtime.dns_no_system_drop_enable(enable)
        return 0, None

    def no_proxy_ips_add(self, byte_data: bytes):
        try:
            rs = zlib.decompress(byte_data)
        except:
            return 0, False

        try:
            text = rs.decode()
        except:
            return 0, False

        try:
            _list = json.loads(text)
        except:
            return 0, False

        self.__runtime.set_no_proxy_ips(_list)
        return 0, True

    def enable_sec_dns(self, enable: bool):
        """是否开启安全DNS
        """
        self.__runtime.enable_sec_dns(enable)
        return 0, None

    def is_enabled_sec_dns(self):
        return 0, self.__runtime.is_enabled_sec_dns()

    def set_sec_dns_forward(self, port: int, key: bytes):
        if port < 1 or port > 65535:
            return 0, False

        if len(key) != 4 or not isinstance(key, bytes):
            return 0, False

        self.__runtime.set_sec_dns_forward(port, key)

        return 0, True

    def add_sec_dns_domains(self, domains: list):
        self.__runtime.add_sec_dns_domains(domains)

        return 0, None

    def del_sec_dns_domains(self, domains: list):
        self.__runtime.del_sec_dns_domains(domains)

        return 0, None

    def set_dns_cache_timeout(self, seconds: int):
        return 0, self.__runtime.set_dns_cache_timeout(seconds)

    def clear_dns_cache(self):
        self.__runtime.clear_dns_cache()
        return 0, None
