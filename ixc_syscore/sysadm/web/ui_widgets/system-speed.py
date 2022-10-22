#!/usr/bin/env python3
import ixc_syslib.web.ui_widget as ui_widget
import ixc_syslib.pylib.RPCClient as RPC


class widget(ui_widget.widget):
    def handle(self, *args, **kwargs):
        configs = RPC.fn_call("router", "/config", "router_config_get")
        system_cpus = RPC.fn_call("router", "/config", "cpu_num")

        uri = "system-speed.html"

        return True, uri, {"configs": configs, "cpu_num": int(system_cpus)}
