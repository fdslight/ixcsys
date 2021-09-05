#!/usr/bin/env python3
# 配置认证类型

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
        _type = self.request.get_argument("type", is_seq=False, is_qs=False)
        if _type not in ("mac", "account",):
            self.json_resp(True, "wrong auth type value")
            return

        diskless_cfg = self.sysadm.diskless_cfg
        diskless_cfg["public"]["auth_type"] = _type
        self.sysadm.save_diskless_cfg()

        self.json_resp(False, None)
