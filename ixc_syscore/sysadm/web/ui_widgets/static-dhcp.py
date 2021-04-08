#!/usr/bin/env python3
import ixc_syslib.web.ui_widget as ui_widget
import ixc_syslib.pylib.RPCClient as RPC


class widget(ui_widget.widget):
    def handle(self, *args, **kwargs):
        ip_bind = RPC.fn_call("DHCP", "/dhcp_server", "get_ip_bind_configs")

        return True, "static-dhcp.html", ip_bind
