#!/usr/bin/env python3

import ixc_syslib.web.controllers.staticfiles as staticfiles


class controller(staticfiles.controller):
    def staticfile_init(self):
        self.set_mime("map", "application/json;charset=utf-8")
        self.set_no_cache()
