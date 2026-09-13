#!/usr/bin/env python3
import os

import ixc_syscore.sysadm.web.controllers.controller as base_controller


class controller(base_controller.BaseController):
    def myinit(self):
        self.request.set_allow_methods(["POST"])
        return True

    def save_script(self, content: str):
        script_path = "%s/expand.start" % os.getenv("IXC_MYAPP_CONF_DIR")
        with open(script_path, "w") as f:
            f.write(content)
        f.close()

    def handle(self):
        script_content = self.request.get_argument("script-content", is_seq=False, is_qs=False, default="")

        if script_content == "":
            script_content = "#!/bin/sh"
            self.save_script(script_content)
            self.json_resp(False, "修改成功")
            return

        script_content = script_content.replace("\r\n", "\n")
        _list = script_content.split("\n")

        if _list[0].find("#!") != 0:
            self.json_resp(True, "首行必须以#!开头用以指定启动程序")
            return

        first_line = _list[0]
        s = first_line[2:]
        x_list = s.split(" ")

        if len(x_list) < 1:
            self.json_resp(True, "首行未指定脚本启动程序")
            return

        if not os.path.isfile(x_list[0]):
            self.json_resp(True, "未找到脚本启动程序%s" % x_list[0])
            return

        self.save_script(script_content)
        self.json_resp(True, "脚本修改成功")

        # self.json_resp(False, {})
