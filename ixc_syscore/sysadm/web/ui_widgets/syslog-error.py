#!/usr/bin/env python3
import ixc_syslib.web.ui_widget as ui_widget
import ixc_syslib.pylib.RPCClient as RPC


class widget(ui_widget.widget):
    def handle(self, *args, **kwargs):
        errlog = RPC.fn_call("init", "/syslog", "errlog_get")
        errlog = errlog.replace("<", "&lt;")
        errlog = errlog.replace(">", "&gt;")

        return True, "syslog-error.html", {"syslog": errlog}
