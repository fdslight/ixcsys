#!/usr/bin/env python3
import ixc_syslib.web.ui_widget as ui_widget
import ixc_syslib.pylib.RPCClient as RPC


class widget(ui_widget.widget):
    def handle(self, *args, **kwargs):
        configs = RPC.fn_call("router", "/config", "lan_config_get")
        if_config = configs["if_config"]
        enable_static_ipv6 = if_config["enable_static_ipv6"]
        enable_ipv6_pass = if_config["enable_ipv6_pass"]
        ip6_addr = if_config["ip6_addr"]
        enable_ipv6_security = if_config["enable_ipv6_security"]

        configs = {
            "enable_static_ipv6": enable_static_ipv6,
            "enable_ipv6_pass": enable_ipv6_pass,
            "enable_ipv6_security": bool(int(enable_ipv6_security)),
            "ip6_addr": ip6_addr
        }

        return True, "ipv6.html", configs
