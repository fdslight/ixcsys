#!/usr/bin/env python3

import ixc_syslib.pylib.RPCClient as RPCClient
import ixc_syslib.web.controllers.rpc_controller as rpc
from pywind.global_vars import global_vars


class controller(rpc.controller):
    @property
    def dhcp(self):
        return global_vars["ixcsys.DHCP"]

    def rpc_init(self):
        self.fobjs = {
            "get_configs": self.get_configs,
            "enable": self.enable,
            "boot_file_set": self.boot_file_set,
            "alloc_addr_range_set": self.alloc_addr_range_set,
            "set_boot_ext_option": self.set_boot_ext_option,
            "unset_boot_ext_option": self.unset_boot_ext_option,
            "clear_boot_ext_option": self.clear_boot_ext_option,
            "set_dhcp_option": self.set_dhcp_option,
            "save": self.save,
            "add_dhcp_bind": self.add_dhcp_bind,
            "del_dhcp_bind": self.del_dhcp_bind,
            "get_ip_bind_configs": self.get_ip_bind_configs,
            "lease_time_set": self.lease_time_set,
            "get_clients": self.get_clients,
            "tftp_config_get": self.tftp_config_get,
            "tftp_dir_set": self.tftp_dir_set,
            "ieee_mac_alloc_info_get": self.ieee_mac_alloc_info_get,
        }

    def get_configs(self):
        return 0, self.dhcp.server_configs

    def enable(self, enable: bool):
        if enable:
            v = 1
        else:
            v = 0
        self.dhcp.server_configs["public"]["enable"] = v

        return 0, True

    def boot_file_set(self, type_key_val: str, boot_file: str):
        self.dhcp.server_configs["public"][type_key_val] = boot_file

        return 0, True

    def alloc_addr_range_set(self, addr_begin: str, addr_end: str):
        self.dhcp.server_configs["public"]["range_begin"] = addr_begin
        self.dhcp.server_configs["public"]["range_end"] = addr_end

        return 0, True

    def get_ip_bind_configs(self):
        return 0, self.dhcp.dhcp_ip_bind

    def set_boot_ext_option(self, hwaddr: str, code: int, value: str):
        return 0, self.dhcp.server.set_boot_ext_option(hwaddr, code, value)

    def unset_boot_ext_option(self, hwaddr: str):
        return 0, self.dhcp.server.unset_boot_ext_option(hwaddr)

    def clear_boot_ext_option(self):
        return 0, self.dhcp.server.clear_boot_ext_option()

    def set_dhcp_option(self, code: int, value: bytes):
        if not isinstance(code, int) or not isinstance(value, bytes):
            return RPCClient.ERR_ARGS, None

        self.dhcp.server.set_dhcp_option(code, value)

        return RPCClient.ERR_NO, None

    def save(self):
        self.dhcp.save_dhcp_server_configs()
        self.dhcp.save_tftp_configs()

        return 0, None

    def add_dhcp_bind(self, alias_name: str, hwaddr: str, ipaddr: str):
        configs = self.dhcp.dhcp_ip_bind
        configs[alias_name] = {"hwaddr": hwaddr, "address": ipaddr}

        self.dhcp.save_ip_bind_configs()

        return 0, True

    def del_dhcp_bind(self, ipaddr: str):
        configs = self.dhcp.dhcp_ip_bind
        alias_name = None

        for k in configs:
            o = configs[k]
            if o["address"] != ipaddr: continue
            alias_name = k
            break

        if not alias_name: return 0, False
        del configs[alias_name]
        self.dhcp.save_ip_bind_configs()

        return 0, True

    def lease_time_set(self, timeout: int):
        try:
            timeout = int(timeout)
        except ValueError:
            return RPCClient.ERR_ARGS, "wrong timeout value type"

        if timeout < 600 or timeout > 86400:
            return RPCClient.ERR_ARGS, "wrong argument value range"

        self.dhcp.server_configs["public"]["lease_time"] = timeout
        return 0, None

    def get_clients(self):
        """获取客户端
        """
        ieee_mac_map = self.dhcp.ieee_mac_info
        clients = self.dhcp.server.get_clients()
        results = []
        for dic in clients:
            hwaddr = dic["hwaddr"]
            ip = dic["ip"]
            host_name = dic["host_name"]
            t = hwaddr.replace(":", "")
            k = t[0:6].upper()

            o = {
                "hwaddr": hwaddr,
                "ip": ip,
                "vendor": ieee_mac_map.get(k, "unkown"),
                "host_name": host_name
            }
            results.append(o)

        return 0, results

    def tftp_config_get(self):
        return 0, self.dhcp.tftp_configs

    def tftp_dir_set(self, d: str):
        configs = self.dhcp.tftp_configs
        conf = configs["conf"]
        conf["file_dir"] = d

        return 0, None

    def ieee_mac_alloc_info_get(self):
        return 0, self.dhcp.ieee_mac_info
