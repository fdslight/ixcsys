#!/usr/bin/env python3
import ixc_syslib.web.ui_widget as ui_widget
import ixc_syslib.pylib.RPCClient as RPC


class widget(ui_widget.widget):
    def handle(self, *args, **kwargs):
        router_configs = RPC.fn_call("router", "/config", "router_config_get")

        qos = router_configs["qos"]

        udp_udplite_first = bool(int(qos["udp_udplite_first"]))

        configs = {
            "udp_udplite_first": udp_udplite_first,
        }

        return True, "net-advanced.html", configs
