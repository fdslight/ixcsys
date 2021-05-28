#!/usr/bin/env python3
import ixc_syslib.web.ui_widget as ui_widget
from pywind.global_vars import global_vars


class widget(ui_widget.widget):
    @property
    def sysadm(self):
        return global_vars["ixcsys.sysadm"]

    def handle(self, *args, **kwargs):
        status = self.sysadm.cloud_service_status
        cloud_service_cfg = self.sysadm.cloud_service_cfg.copy()

        st = ""

        if cloud_service_cfg["enable"]:
            st = "conn_ok"

        if cloud_service_cfg["enable"] and not status:
            st = "no_conn"

        if not cloud_service_cfg["enable"]:
            st = "no_enable"

        cloud_service_cfg["status"] = st

        return True, "cloud-service.html", cloud_service_cfg
