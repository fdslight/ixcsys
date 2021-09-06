#!/usr/bin/env python3
import os
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

    def send_os(self, hwaddr: str):
        """发送操作系统列表
        """
        os_info = self.sysadm.diskless_os_cfg_get(hwaddr)
        script_path = os_info["script-path"]

        if not os.path.isfile(script_path):
            self.send_exit("not found iPXE script %s for mac address %s" % (script_path, hwaddr,))
            return

        fd = open(script_path, "rb")
        byte_s = fd.read()
        fd.close()

        self.finish_with_bytes("application/octet-stream", byte_s)

    def send_exit(self, reason=None):
        """发送退出
        """
        self.finish_with_text("")

    def handle(self):
        hwaddr = self.request.get_argument("hwaddr", is_seq=False, is_qs=True)
        if not hwaddr:
            self.send_exit("not set mac address")
            return
        hwaddr = hwaddr.lower()
        self.send_os(hwaddr)
