#!/usr/bin/env python3

import ixc_syscore.sysadm.web.controllers.controller as base_controller
import ixc_syslib.pylib.RPCClient as RPC

import pywind.lib.netutils as netutils


class controller(base_controller.BaseController):
    def myinit(self):
        self.request.set_allow_methods(["POST"])
        return True

    def handle(self):
        s_enable_dhcp = self.request.get_argument("enable_dhcp", is_seq=False, is_qs=False)
        addr_begin = self.request.get_argument("addr_begin", is_seq=False, is_qs=False)
        addr_end = self.request.get_argument("addr_end", is_seq=False, is_qs=False)
        boot_file = self.request.get_argument("boot_file", is_seq=False, is_qs=False)
        lease_time = self.request.get_argument("lease_time", is_seq=False, is_qs=False)
        x64_efi_boot_file = self.request.get_argument("x64_efi_boot_file", is_seq=False, is_qs=False)
        x86_pc_boot_file = self.request.get_argument("x86_pc_boot_file", is_seq=False, is_qs=False)

        if not addr_begin or not addr_end or not boot_file or not lease_time:
            self.json_resp(True, "不能提交空的选项")
            return

        if not netutils.is_ipv4_address(addr_begin):
            self.json_resp(True, "错误的起始地址格式")
            return

        if not netutils.is_ipv4_address(addr_end):
            self.json_resp(True, "错误的结束地址格式")
            return

        if not boot_file or not x86_pc_boot_file or not x64_efi_boot_file:
            self.json_resp(True, "引导文件不能为空")
            return

        if len(boot_file) > 500 or len(x86_pc_boot_file) > 500 or len(x64_efi_boot_file) > 500:
            self.json_resp(True, "引导文件名过长,最大只能是500字节")
            return

        try:
            lease_time = int(lease_time)
        except ValueError:
            self.json_resp(True, "错误的DHCP租期时间,时间只能为数字")
            return

        if lease_time < 600 or lease_time > 86400:
            self.json_resp(True, "DHCP租期最小是10分钟,最长1天")
            return

        if not s_enable_dhcp:
            enable_dhcp = False
        else:
            enable_dhcp = True

        RPC.fn_call("DHCP", "/dhcp_server", "enable", enable_dhcp)

        RPC.fn_call("DHCP", "/dhcp_server", "boot_file_set", "boot_file", boot_file)
        RPC.fn_call("DHCP", "/dhcp_server", "boot_file_set", "x64_efi_boot_file", x64_efi_boot_file)
        RPC.fn_call("DHCP", "/dhcp_server", "boot_file_set", "x86_pc_boot_file", x86_pc_boot_file)

        RPC.fn_call("DHCP", "/dhcp_server", "alloc_addr_range_set", addr_begin, addr_end)
        RPC.fn_call("DHCP", "/dhcp_server", "lease_time_set", lease_time)
        RPC.fn_call("DHCP", "/dhcp_server", "save")

        self.json_resp(False, {})
