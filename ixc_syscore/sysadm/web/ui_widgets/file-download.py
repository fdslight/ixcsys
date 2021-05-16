#!/usr/bin/env python3
import ixc_syslib.web.ui_widget as ui_widget
from pywind.global_vars import global_vars


class widget(ui_widget.widget):
    @property
    def sysadm(self):
        return global_vars["ixcsys.sysadm"]

    @property
    def enable_download(self):
        cfg = self.sysadm.download_cfg
        return bool(int(cfg["enable"]))

    @property
    def download_dir(self):
        cfg = self.sysadm.download_cfg
        return cfg["dir"]

    def handle(self, *args, **kwargs):
        return True, "file-download.html", {"enable": self.enable_download, "dir": self.download_dir}
