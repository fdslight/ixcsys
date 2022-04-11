#!/usr/bin/env python3

import ixc_syslib.web.controllers.staticfiles as staticfiles
from pywind.global_vars import global_vars


class controller(staticfiles.controller):
    @property
    def debug(self):
        return global_vars["ixcsys.sysadm"].debug

    def staticfile_init(self):
        self.set_debug(self.debug)
        self.set_mime("map", "application/json;charset=utf-8")
        self.set_no_cache()
