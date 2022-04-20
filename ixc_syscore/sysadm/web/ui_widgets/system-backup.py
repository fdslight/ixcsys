#!/usr/bin/env python3
import os
import ixc_syslib.web.ui_widget as ui_widget


class widget(ui_widget.widget):
    def handle(self, *args, **kwargs):
        d = "/var/log"
        files = []
        for x in os.listdir(d):
            p = x.find("ixcsys_config_backup.")
            if p != 0: continue
            path = "%s/%s" % (d, x,)
            if not os.path.isfile(path): continue
            files.append(x)

        return True, "system-backup.html", {"backup-files": files}
