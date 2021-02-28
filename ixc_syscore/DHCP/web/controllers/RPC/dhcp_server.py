#!/usr/bin/env python3

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
            "save": self.save,
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

    def boot_file_set(self, boot_file: str):
        self.dhcp.server_configs["public"]["boot_file"] = boot_file

        return 0, True

    def alloc_addr_range_set(self, addr_begin: str, addr_end: str):
        self.dhcp.server_configs["public"]["range_begin"] = addr_begin
        self.dhcp.server_configs["public"]["range_end"] = addr_end

        return 0, True

    def save(self):
        self.dhcp.save_dhcp_server_configs()

        return 0, None
