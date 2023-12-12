#!/usr/bin/env python3

import os, struct
import ixc_syslib.web.ui_widget as ui_widget


class widget(ui_widget.widget):
    def read_update_time(self):
        fpath = "%s/auto_update.time" % self.sys_dir
        if not os.path.isfile(fpath): return -1
        with open(fpath, "rb") as f:
            t = f.read()
        f.close()
        if len(t) != 4: return -1

        seconds, = struct.unpack("I", t)

        return seconds

    def handle(self, *args, **kwargs):
        uri = "auto-update.html"
        seconds = self.read_update_time()
        if seconds < 0:
            h = "0"
            m = "0"
        else:
            h = str(int(seconds / 3600))
            m = str(int((seconds - seconds / 3600 * 3600) / 60))

        return True, uri, {"h": h, "m": m}
