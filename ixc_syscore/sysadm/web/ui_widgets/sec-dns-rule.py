#!/usr/bin/env python3
import ixc_syslib.web.ui_widget as ui_widget
import ixc_syslib.pylib.RPCClient as RPC


class widget(ui_widget.widget):
    def handle(self, *args, **kwargs):
        rules = RPC.fn_call("DNS", "/rule", "get_sec_rules")
        uri = "sec-dns-rule.html"
        s="\r\n".join(rules)

        return True, uri, {"rules": s}
