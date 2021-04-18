#!/usr/bin/env python3
import ixc_syslib.web.ui_widget as ui_widget
import ixc_syslib.pylib.RPCClient as RPC


class widget(ui_widget.widget):
    def handle(self, *args, **kwargs):
        clients = RPC.fn_call("DHCP", "/dhcp_server", "get_clients")

        # 此处转换bytes host_name编码
        for dic in clients:
            host_name = dic["host_name"]
            if not host_name:
                host_name = "-"
            else:
                host_name = host_name.decode("iso-8859-1")
            dic["host_name"] = host_name

        return True, "dhcp-host.html", {"clients": clients}
