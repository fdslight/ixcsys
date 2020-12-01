#!/usr/bin/env python3
import ixc_syslib.web.ui_widget as ui_widget
import ixc_syslib.pylib.RPCClient as RPC


class widget(ui_widget.widget):
    def handle(self, *args, **kwargs):
        if RPC.RPCReadyOk("DHCP"):
            configs = RPC.fn_call("DHCP", "/dhcp_server", "get_configs")
        else:
            configs = {}

        return True, "dhcp-server.html", configs
