#!/usr/bin/env python3
import ixc_syslib.web.ui_widget as ui_widget
import ixc_syslib.pylib.RPCClient as RPC


class widget(ui_widget.widget):
    def handle(self, *args, **kwargs):
        if RPC.RPCReadyOk("router"):
            configs = RPC.fn_call("router", "/config", "router_config_get")
            uri = "ip-rewrite-for-pass.html"
            rs = configs["rewrite_for_pass"]
        else:
            uri = "no-proc.html"
            rs = {"proc_name": "DHCP"}

        return True, uri, rs
