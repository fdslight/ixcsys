#!/usr/bin/env python3
import os, time

import ixc_syscore.sysadm.web.controllers.controller as base_controller

from pywind.global_vars import global_vars


class controller(base_controller.BaseController):
    def myinit(self):
        self.request.set_allow_methods(["POST"])
        return True

    @property
    def sysadm(self):
        return global_vars["ixcsys.sysadm"]

    def do_backup(self):
        t = time.strftime("%Y-%m-%d_%H%M%S")
        fpath = "/var/log/ixcsys_config_backup.%s.tar.gz" % t
        os.system("tar czf %s /opt/ixcsys/ixc_configs" % fpath)

        self.json_resp(False, "备份成功")

    def handle(self):
        action = self.request.get_argument("do", is_seq=False, is_qs=False)
        if action not in ("delete", "recovery", "backup",):
            self.json_resp(True, "错误的请求参数")
            return

        if action == "backup":
            self.do_backup()
            return

        file_name = self.request.get_argument("file", is_seq=False, is_qs=False)
        if not file_name:
            self.json_resp(True, "非法的文件名")
            return

        # 检查文件是否合法,避免提交参数随意操作不允许的文件
        p = file_name.find("ixcsys_config_backup.")
        if p != 0:
            self.json_resp(True, "非法的文件名")
            return

        fpath = "/var/log/%s" % file_name
        if not os.path.isfile(fpath):
            self.json_resp(True, "不存在文件%s" % file_name)
            return

        if action == "delete":
            os.remove(fpath)
            msg = ""
        else:
            os.system("tar xzf %s -C /" % fpath)
            msg = "恢复成功,请重启路由器"

        self.json_resp(False, msg)
