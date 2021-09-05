#!/usr/bin/env python3
import hashlib
import ixc_syscore.sysadm.web.controllers.controller as base_controller
from pywind.global_vars import global_vars


class controller(base_controller.BaseController):
    def myinit(self):
        self.request.set_allow_methods(["GET"])
        return True

    @property
    def sysadm(self):
        return global_vars["ixcsys.sysadm"]

    def send_script(self, script: str):
        self.finish_with_bytes("application/octet-stream", script.encode())

    def send_os_list(self, hwaddr: str):
        """发送操作系统列表
        """
        os_list = self.sysadm.diskless_os_cfg_get(hwaddr)
        _list = ["#!ipxe", "\n", ]

    def send_exit(self, reason=None):
        """发送退出
        """
        pass

    def handle(self):
        hwaddr = self.request.get_argument("hwaddr", is_seq=False, is_qs=True)
        self.send_os_list("mac", hwaddr)

