#!/usr/bin/env python3
import ixc_syslib.web.ui_widget as ui_widget
import ixc_syslib.pylib.RPCClient as RPC


class widget(ui_widget.widget):
    def handle(self, *args, **kwargs):
        if RPC.RPCReadyOk("DHCP"):
            configs = RPC.fn_call("DHCP", "/dhcp_server", "get_configs")
            b = configs["public"]["enable"]
            configs["public"]["enable"] = bool(int(b))
            uri = "dhcp-server.html"
            rs = configs
            print(rs)
        else:
            uri = "no-proc.html"
            rs = {"proc_name": "DHCP"}

        return True, uri, rs
