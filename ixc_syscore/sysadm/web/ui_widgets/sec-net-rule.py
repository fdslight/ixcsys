#!/usr/bin/env python3
import ixc_syslib.web.ui_widget as ui_widget
import ixc_syslib.pylib.RPCClient as RPC


class widget(ui_widget.widget):
    def handle(self, *args, **kwargs):
        configs = RPC.fn_call("router", "/config", "sec_net_config_get")
        uri = "sec-net-rule.html"

        return True, uri, configs
