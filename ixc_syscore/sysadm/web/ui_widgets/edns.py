#!/usr/bin/env python3
import ixc_syslib.web.ui_widget as ui_widget
import ixc_syslib.pylib.RPCClient as RPC


class widget(ui_widget.widget):
    def handle(self, *args, **kwargs):
        dns_servers = RPC.fn_call("secDNS", "/config", "dot_servers_get")
        uri = "edns.html"
        for server in dns_servers:
            if "port" not in server:
                server["port"] = '853'
            ''''''
        return True, uri, {"servers": dns_servers}
