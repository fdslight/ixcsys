#!/usr/bin/env python3
import ixc_syslib.web.ui_widget as ui_widget
import ixc_syslib.pylib.RPCClient as RPC


class widget(ui_widget.widget):
    def handle(self, *args, **kwargs):
        errlog = RPC.fn_call("init", "/syslog", "errlog_get")
        syslog = RPC.fn_call("init", "/syslog", "syslog_get")

        return True, "syslog.html", {"error": errlog, "syslog": syslog}
