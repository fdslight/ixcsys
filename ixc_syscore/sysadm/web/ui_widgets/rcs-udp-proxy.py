#!/usr/bin/env python3

from pywind.global_vars import global_vars

import ixc_syslib.web.ui_widget as ui_widget


class widget(ui_widget.widget):
    @property
    def sysadm(self):
        return global_vars["ixcsys.sysadm"]

    def handle(self, *args, **kwargs):
        config = self.sysadm.udp_n2n_configs

        return True, "rcs-udp-proxy.html", config
