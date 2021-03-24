#!/usr/bin/env python3
import pywind.lib.configfile as conf
import ixc_syslib.web.ui_widget as ui_widget


class widget(ui_widget.widget):
    def handle(self, *args, **kwargs):
        fpath = "%s/wake_on_lan.ini" % self.my_conf_dir
        configs = conf.ini_parse_from_file(fpath)

        return True, "wake-on-lan.html", configs
