#!/usr/bin/env python3

import json
import ixc_syslib.web.controllers.ui_controller as base


class BaseController(base.controller):
    @property
    def user_configs(self):
        conf_path = "%s/user.json" % self.my_config_dir

        with open(conf_path, "r") as f: s = f.read()
        f.close()

        return json.loads(s)

