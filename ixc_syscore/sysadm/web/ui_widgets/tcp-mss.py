#!/usr/bin/env python3
import ixc_syslib.web.ui_widget as ui_widget
import ixc_syslib.pylib.RPCClient as RPC


class widget(ui_widget.widget):
    def handle(self, *args, **kwargs):
        configs = RPC.fn_call("router", "/config", "router_config_get")
        conf = configs["config"]

        uri = "tcp-mss.html"

        return True, uri, {"ip6_tcp_mss": conf["ip6_tcp_mss"], "ip_tcp_mss": conf["ip_tcp_mss"]}
