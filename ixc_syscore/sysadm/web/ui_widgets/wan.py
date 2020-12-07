#!/usr/bin/env python3
import ixc_syslib.web.ui_widget as ui_widget
import ixc_syslib.pylib.RPCClient as RPC


class widget(ui_widget.widget):

    def handle(self, *args, **kwargs):
        _type = self.get_argument("type", default="pppoe", is_qs=True, is_seq=False)

        if _type not in ("pppoe", "dhcp", "static-ip",): _type = "pppoe"
        kwargs = {}
        configs = RPC.fn_call("router", "/config", "wan_config_get")

        if _type == "pppoe":
            kwargs = configs["pppoe"]
            kwargs["heartbeat"] = bool(int(kwargs["heartbeat"]))
        if _type == "static-ip":
            kwargs = configs["ipv4"]

        if _type == "dhcp":
            kwargs = configs["dhcp"]
            kwargs["positive_heartbeat"] = bool(int(kwargs["positive_heartbeat"]))

        return True, "wan.html", kwargs
