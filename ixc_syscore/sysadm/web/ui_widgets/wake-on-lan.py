#!/usr/bin/env python3
import json
import ixc_syslib.web.ui_widget as ui_widget


class widget(ui_widget.widget):
    def handle(self, *args, **kwargs):
        fpath = "%s/wake_on_lan.json" % self.my_conf_dir

        with open(fpath, "r") as f: s = f.read()
        f.close()
        s=s.encode().decode("latin-1")
        o = json.loads(s)

        return True, "wake-on-lan.html", o
