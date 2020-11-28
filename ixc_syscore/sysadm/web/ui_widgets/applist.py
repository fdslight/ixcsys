#!/usr/bin/env python3
import ixc_syslib.web.ui_widget as ui_widget


class widget(ui_widget.widget):
    def handle(self, *args, **kwargs):
        return True, "applist.html", {"apps": self.request_handler.get_all_apps()}
