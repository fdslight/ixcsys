#!/usr/bin/env python3
import ixc_syslib.web.ui_widget as ui_widget
from pywind.global_vars import global_vars


class widget(ui_widget.widget):
    @property
    def sysadm(self):
        return global_vars["ixcsys.sysadm"]

    def handle(self, *args, **kwargs):
        configs = self.sysadm.diskless_cfg_macs
        uri = "diskless.html"

        return True, uri, configs
