#!/usr/bin/env python3

import json
import ixc_syslib.web.ui_widget as ui_widget
import ixc_syslib.pylib.RPCClient as RPC


class widget(ui_widget.widget):
    def handle(self, *args, **kwargs):
        port_map_configs = RPC.fn_call("router", "/config", "port_map_configs_get")

        return True, "port-map.html", port_map_configs
