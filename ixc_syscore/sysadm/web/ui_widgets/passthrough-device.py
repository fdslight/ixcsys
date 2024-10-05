#!/usr/bin/env python3
import ixc_syslib.web.ui_widget as ui_widget
import ixc_syslib.pylib.RPCClient as RPC


class widget(ui_widget.widget):
    def handle(self, *args, **kwargs):
        router_configs = RPC.fn_call("router", "/config", "router_config_get")
        passthrough_devices = router_configs["passthrough"]
        print(passthrough_devices)
        uri = "passthrough-device.html"
        return True, uri, {"devices": passthrough_devices}
