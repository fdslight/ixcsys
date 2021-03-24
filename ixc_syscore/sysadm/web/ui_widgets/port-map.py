#!/usr/bin/env python3

import json
import ixc_syslib.web.ui_widget as ui_widget
import ixc_syslib.pylib.RPCClient as RPC


class widget(ui_widget.widget):
    def handle(self, *args, **kwargs):
        port_map_configs = RPC.fn_call("router", "/config", "port_map_configs_get")

        for name in port_map_configs:
            o = port_map_configs[name]
            protocol = int(o["protocol"])
            if protocol == 6:
                o["protocol"] = "TCP"
            if protocol == 17:
                o["protocol"] = "UDP"
            if protocol == 136:
                o["protocol"] = "UDPLite"

        return True, "port-map.html", port_map_configs
