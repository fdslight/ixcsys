#!/usr/bin/env python3
import sys, os, platform, psutil
import ixc_syslib.web.ui_widget as ui_widget


class widget(ui_widget.widget):
    def get_system_info(self):
        sys_info = {
            "os_type": sys.platform,
            "arch": platform.machine(),
            "cpu_count": os.cpu_count(),
            "mem_tot_size": psutil.virtual_memory().total,
            "mem_free_size": psutil.virtual_memory().free,
            "ixcsys_version": "1.0.0-b1"
        }
        return sys_info

    def handle(self, *args, **kwargs):
        return True, "system-info.html", self.get_system_info()
