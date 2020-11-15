#!/usr/bin/env python3

import sys, platform, os, psutil
import ixc_syscore.sysadm.web.controllers.controller as base_controller


class controller(base_controller.BaseController):
    def myinit(self):
        self.request.set_allow_methods(["GET"])
        return True

    def handle(self):
        sys_info = {
            "os_type": sys.platform,
            "arch": platform.machine(),
            "cpu_count": os.cpu_count(),
            "mem_tot_size": psutil.virtual_memory().total,
            "mem_free_size": psutil.virtual_memory().free,
            "ixcsys_version": "1.0.0-b1"
        }
        self.finish_with_json(sys_info)
