#!/usr/bin/env python3
import ixc_syslib.web.ui_widget as ui_widget
import ixc_syscore.sysadm.pylib.ixcproc as ixcproc


class widget(ui_widget.widget):
    def handle(self, *args, **kwargs):
        proc_list = ixcproc.ixc_running_proc_get()

        return True, "proc-manage.html", {"proc_list": proc_list}
