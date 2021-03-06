#!/usr/bin/env python3
import ixc_syslib.web.ui_widget as ui_widget
import ixc_syslib.pylib.RPCClient as RPC


class widget(ui_widget.widget):
    def handle(self, *args, **kwargs):
        if RPC.RPCReadyOk("tftp"):
            configs = RPC.fn_call("tftp", "/config", "config_get")
            configs["enable_ipv6"] = bool(int(configs["enable_ipv6"]))
            uri = "tftp.html"
            rs = configs
        else:
            configs = {}
            uri = "no-proc.html"
            rs = {"proc_name": "tftp"}

        return True, uri, rs
