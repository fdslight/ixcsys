#!/usr/bin/env python3
import ixc_syslib.web.ui_widget as ui_widget
import ixc_syslib.pylib.RPCClient as RPC


class widget(ui_widget.widget):
    def handle(self, *args, **kwargs):
        rs = RPC.fn_call("router", "/config", "net_monitor_config_get")

        uri = "sec-net-monitor.html"

        rs["enable"] = bool(int(rs["enable"]))

        return True, uri, rs
