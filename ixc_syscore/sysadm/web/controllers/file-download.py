#!/usr/bin/env python3

import os
import ixc_syscore.sysadm.web.controllers.controller as base_controller

from pywind.global_vars import global_vars


class controller(base_controller.BaseController):
    def myinit(self):
        self.request.set_allow_methods(["POST"])
        return True

    @property
    def sysadm(self):
        return global_vars["ixcsys.sysadm"]

    def handle(self):
        enable = self.request.get_argument("enable", is_seq=False, is_qs=False)
        d = self.request.get_argument("dir", is_seq=False, is_qs=False)

        if not d:
            self.json_resp(True, "文件目录不能为空")
            return

        if enable:
            e = True
        else:
            e = False

        if not os.path.isdir(d):
            self.json_resp(True, "%s 不是一个目录" % d)
            return

        self.sysadm.set_file_download(e, d=d)
        self.sysadm.save_file_download_cfg()
        self.json_resp(False, "")
