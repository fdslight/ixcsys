#!/usr/bin/env python3

import ixc_syslib.web.controllers.rpc_controller as rpc
from pywind.global_vars import global_vars


class controller(rpc.controller):
    @property
    def _pass(self):
        return global_vars["ixcsys.PASS"]

    def rpc_init(self):
        self.fobjs = {
            "config_get": self.configs_get,
            "config_save": self.config_save,
        }

    def configs_get(self):
        return 0, self._pass.configs

    def config_save(self, configs: dict):
        old_configs = self._pass.configs
        old_configs['config'] = configs

        return 0, self._pass.save_config()
