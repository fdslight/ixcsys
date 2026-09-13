#!/usr/bin/env python3
import os
import ixc_syslib.web.ui_widget as ui_widget


class widget(ui_widget.widget):
    def handle(self, *args, **kwargs):
        script_path = "%s/expand.start" % os.getenv("IXC_MYAPP_CONF_DIR")
        if not os.path.isfile(script_path):
            script_content = ""
        else:
            with open(script_path, "r", errors='ignore') as f:
                script_content = f.read()
            f.close()

        return True, "system-expand.html", {"script_content": script_content}
