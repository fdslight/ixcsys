#!/usr/bin/env python3
import os
import ixc_syscore.sysadm.web.controllers.controller as base_controller
from urllib import parse
from pywind.global_vars import global_vars


class controller(base_controller.BaseController):
    def myinit(self):
        self.set_auto_auth(False)
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

        if not os_info:
            self.send_exit(reason="not found config for %s" % hwaddr)
            return

        script_path = os_info["script-path"]

        if not os.path.isfile(script_path):
            self.send_exit(reason="not found iPXE script %s for mac address %s" % (script_path, hwaddr,))
            return

        fd = open(script_path, "rb")
        byte_s = fd.read()
        fd.close()

        _list = byte_s.split(b"\n")
        if not _list:
            self.send_exit("the file %s is empty" % script_path)
            return

        _list.insert(1,
                     "prompt --key 0x02 --timeout 5000 Press Ctrl-B for the iPXE command line... && shell ||".encode())

        byte_s = b"\n".join(_list)
        self.finish_with_bytes("application/octet-stream", byte_s)

    def send_exit(self, reason=None):
        """发送退出
        """
        _list = [
            "#!ipxe\n\n",
            "echo %s\n" % reason,
            "sleep 10\n"
        ]
        self.finish_with_bytes("application/octet-stream", "".join(_list).encode())

    def handle(self):
        hwaddr = self.request.get_argument("hwaddr", is_seq=False, is_qs=True)

        if not hwaddr:
            self.send_exit(reason="not set mac address")
            return

        hwaddr = parse.unquote(hwaddr)
        hwaddr = hwaddr.lower()

        self.send_os(hwaddr)
