#!/usr/bin/env python3
import hashlib

import ixc_syscore.sysadm.web.controllers.controller as base_controller
import pywind.lib.netutils as netutils
from pywind.global_vars import global_vars


class controller(base_controller.BaseController):
    @property
    def sysadm(self):
        return global_vars["ixcsys.sysadm"]

    def init_os_cfg(self):
        return {
            "default_os": None,
            "os_list_wait_timeout": 5,
            "os_list": []
        }

    def myinit(self):
        self.request.set_allow_methods(["POST"])
        return True

    def add_mac(self):
        hwaddr = self.request.get_argument("hwaddr", is_seq=False, is_qs=False)
        cfg_macs = self.sysadm.diskless_cfg_macs

        if not netutils.is_hwaddr(hwaddr):
            self.json_resp(True, "错误的MAC地址格式")
            return

        if hwaddr in cfg_macs:
            self.json_resp(False, None)
            return

        cfg_macs[hwaddr] = self.init_os_cfg()
        self.sysadm.save_diskless_cfg_macs()
        self.json_resp(False, None)

    def del_mac(self):
        hwaddr = self.request.get_argument("hwaddr", is_seq=False, is_qs=False)
        cfg_macs = self.sysadm.diskless_cfg_macs

        if hwaddr not in cfg_macs:
            self.json_resp(False, None)
            return

        del cfg_macs[hwaddr]

        self.sysadm.save_diskless_cfg_macs()
        self.json_resp(False, None)

    def change_mac(self):
        """改变MAC地址
        """
        hwaddr = self.request.get_argument("hwaddr", is_seq=False, is_qs=False)
        new_hwaddr = self.request.get_argument("new_hwaddr", is_seq=False, is_qs=False)

    def handle(self):
        action = self.request.get_argument("action", is_seq=False, is_qs=False)

        if action not in ("add", "delete", "mod",):
            self.json_resp(True, "错误的提交动作类型")
            return

        if action == "add":
            self.add_mac()
        elif action == "mod":
            self.change_mac()
        else:
            self.del_mac()
