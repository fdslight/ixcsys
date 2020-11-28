#!/usr/bin/env python3

import json, os
import ixc_syslib.web.controllers.ui_controller as base


class BaseController(base.controller):
    @property
    def user_configs(self):
        conf_path = "%s/user.json" % self.my_config_dir

        with open(conf_path, "r") as f: s = f.read()
        f.close()

        return json.loads(s)

    def json_resp(self, is_error: bool, message):
        """响应ajax
        """
        self.finish_with_json({"is_error": is_error, "message": message})

    def is_valid_app(self, app_name: str):
        """检查是否是合法的应用
        """
        return True

    def get_app_info(self, app_name: str):
        """获取应用信息
        """
        return {"name": app_name, "t_name": "测试应用".encode().decode("iso-8859-1")}

    def get_all_apps(self):
        """获取所有应用信息"""
        _list = os.listdir(self.app_dir)
        results = []

        for x in _list:
            path = "%s/%s" % (self.app_dir, x,)

            if not os.path.isdir(path): continue
            if not self.is_valid_app(x): continue

            results.append(self.get_app_info(x))
        return results
