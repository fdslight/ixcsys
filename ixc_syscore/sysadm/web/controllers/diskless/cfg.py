#!/usr/bin/env python3

import ixc_syscore.sysadm.web.controllers.controller as base_controller
import pywind.lib.netutils as netutils

from pywind.global_vars import global_vars


class controller(base_controller.BaseController):
    @property
    def sysadm(self):
        return global_vars["ixcsys.sysadm"]

    def myinit(self):
        self.request.set_allow_methods(["POST"])
        return True

    def add_mac(self):
        name = self.request.get_argument("name", is_seq=False, is_qs=False)
        hwaddr = self.request.get_argument("hwaddr", is_seq=False, is_qs=False)
        initiator_name = self.request.get_argument("iscsi_initiator_iqn", is_seq=False, is_qs=False)
        root_path = self.request.get_argument("iscsi_target_iqn", is_seq=False, is_qs=False)
        script_path = self.request.get_argument("script-path", is_seq=False, is_qs=False)

        cfg_macs = self.sysadm.diskless_cfg_macs

        if not name:
            self.json_resp(True, "别名不能为空")
            return

        if not hwaddr:
            self.json_resp(True, "网卡MAC地址不能为空")
            return

        if not initiator_name:
            self.json_resp(True, "iSCSI initiator不能为空")
            return

        if not root_path:
            self.json_resp(True, "iSCSI target不能为空")
            return

        if not netutils.is_hwaddr(hwaddr):
            self.json_resp(True, "错误的MAC地址格式")
            return

        if not script_path:
            self.json_resp(True, "iPXE脚本路径不能为空")
            return

        if hwaddr in cfg_macs:
            self.json_resp(True, "机器%s已经存在" % hwaddr)
            return

        if len(root_path.encode()) > 250:
            self.json_resp(True, "iSCSI target长度不能超过250字节")
            return

        hwaddr = hwaddr.lower()

        cfg_macs[hwaddr] = {
            "name": name,
            "initiator-iqn": initiator_name,
            "root-path": root_path,
            "script-path": script_path
        }

        self.sysadm.save_diskless_cfg_macs()
        self.sysadm.reset_diskless()
        self.json_resp(False, None)

    def del_mac(self):
        hwaddr = self.request.get_argument("hwaddr", is_seq=False, is_qs=False)
        cfg_macs = self.sysadm.diskless_cfg_macs

        if not hwaddr:
            self.json_resp(True, "MAC地址不能为空")
            return

        if hwaddr not in cfg_macs:
            self.json_resp(False, None)
            return

        hwaddr = hwaddr.lower()

        del cfg_macs[hwaddr]

        self.sysadm.save_diskless_cfg_macs()
        self.sysadm.reset_diskless()
        self.json_resp(False, None)

    def handle(self):
        action = self.request.get_argument("action", is_seq=False, is_qs=False)

        if action not in ("add", "del",):
            self.json_resp(True, "错误的提交动作类型")
            return

        if action == "add":
            self.add_mac()
        else:
            self.del_mac()
