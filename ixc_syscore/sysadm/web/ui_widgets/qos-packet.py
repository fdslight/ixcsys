#!/usr/bin/env python3
import ixc_syslib.web.ui_widget as ui_widget
import ixc_syslib.pylib.RPCClient as RPC


class widget(ui_widget.widget):
    def handle(self, *args, **kwargs):
        configs = RPC.fn_call("router", "/config", "wan_config_get")
        qos=configs["qos"]

        configs = {
            "mpkt_first_size":qos["mpkt_first_size"],
        }

        return True, "qos-packet.html", configs
