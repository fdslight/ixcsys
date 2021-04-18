#!/usr/bin/env python3
import ixc_syslib.web.ui_widget as ui_widget
import ixc_syslib.pylib.RPCClient as RPC


class widget(ui_widget.widget):
    def handle(self, *args, **kwargs):
        clients = RPC.fn_call("DHCP", "/dhcp_server", "get_clients")

        for dic in clients:
            dic["host_name"] = dic["host_name"].decode("iso-8859-1")

        return True, "dhcp-host.html", {"clients": clients}
