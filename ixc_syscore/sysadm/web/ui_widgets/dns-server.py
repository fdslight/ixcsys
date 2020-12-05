#!/usr/bin/env python3
import ixc_syslib.web.ui_widget as ui_widget
import ixc_syslib.pylib.RPCClient as RPC


class widget(ui_widget.widget):
    def handle(self, *args, **kwargs):
        if RPC.RPCReadyOk("DNS"):
            rs = RPC.fn_call("DNS", "/config", "config_get")
            uri = "dns-server.html"
        else:
            uri = "no-proc.html"
            rs = {"proc_name": "DNS"}

        return True, uri, rs
