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

    def save_sysadm_json_config(self, path: str, o):
        fdst = open(path, "w")
        fdst.write(json.dumps(o))
        fdst.close()

    def get_sysadm_json_config(self, path: str):
        fdst = open(path, "r")
        s = fdst.read()
        fdst.close()

        return json.loads(s)
