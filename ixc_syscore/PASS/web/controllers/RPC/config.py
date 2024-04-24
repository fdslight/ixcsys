#!/usr/bin/env python3

import ixc_syslib.web.controllers.rpc_controller as rpc
from pywind.global_vars import global_vars


class controller(rpc.controller):
    @property
    def _pass(self):
        return global_vars["ixcsys.PASS"]

    def rpc_init(self):
        self.fobjs = {
            "config_get": self.config_get,
            "config_save": self.config_save,
        }

    def config_get(self):
        config = self._pass.configs['config']

        return 0, config

    def config_save(self, configs: dict):
        old_configs = self._pass.configs
        old_configs['config'] = configs
        self._pass.save_configs()

        return 0, None
