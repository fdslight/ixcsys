#!/usr/bin/env python3
import ixc_syslib.web.ui_widget as ui_widget
import ixc_syslib.pylib.RPCClient as RPC


class widget(ui_widget.widget):
    def handle(self, *args, **kwargs):
        _type = self.get_argument("type", default="conn", is_qs=True, is_seq=False)

        if _type not in ("conn", "dns", "pass-ip", "proxy-ip",): _type = "conn"

        configs = RPC.fn_call("proxy", "/config", "config_get", _type)

        return True, "proxy.html", configs
