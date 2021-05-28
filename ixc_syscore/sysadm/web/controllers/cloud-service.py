#!/usr/bin/env python3

import ixc_syscore.sysadm.web.controllers.controller as base_controller
from pywind.global_vars import global_vars


class controller(base_controller.BaseController):
    @property
    def sysadm(self):
        return global_vars["ixcsys.sysadm"]

    def myinit(self):
        self.request.set_allow_methods(["POST"])
        return True

    def handle(self):
        enable = self.request.get_argument("enable", is_seq=False, is_qs=False)
        device_id = self.request.get_argument("device_id", is_seq=False, is_qs=False)
        key_id = self.request.get_argument("key", is_seq=False, is_qs=False)

        if enable and (not device_id or not key_id):
            self.json_resp(True, "不能存在为空的值")
            return

        if device_id:
            if len(device_id) != 16:
                self.json_resp(True, "错误的设备ID值")
                return
            ''''''
        else:
            device_id = ""
        if key_id:
            if len(key_id) > 16:
                self.json_resp(True, "KEY长度最高只能为16")
                return
            ''''''
        else:
            key_id = ""

        cfg = self.sysadm.cloud_service_cfg
        if enable:
            cfg["enable"] = True
        else:
            cfg["enable"] = False

        cfg["device_id"] = device_id
        cfg["key"] = key_id

        self.sysadm.save_cloudservice_cfg()

        self.json_resp(False, {})
