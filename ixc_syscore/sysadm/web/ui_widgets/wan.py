#!/usr/bin/env python3
import ixc_syslib.web.ui_widget as ui_widget
import ixc_syslib.pylib.RPCClient as RPC


class widget(ui_widget.widget):

    def handle(self, *args, **kwargs):
        _type = self.get_argument("type", default="pppoe", is_qs=True, is_seq=False)

        if _type not in ("pppoe", "dhcp", "static-ip",): _type = "pppoe"
        kwargs = {}
        configs = RPC.fn_call("router", "/runtime", "get_wan_configs")

        if _type == "pppoe":
            kwargs = configs["pppoe"]
            kwargs["enable"] = bool(int(kwargs["enable"]))
        if _type == "static-ip":
            kwargs = configs["ipv4"]

        return True, "wan.html", kwargs
