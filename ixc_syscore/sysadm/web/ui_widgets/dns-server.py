#!/usr/bin/env python3
import ixc_syslib.web.ui_widget as ui_widget
import ixc_syslib.pylib.RPCClient as RPC


class widget(ui_widget.widget):
    def handle(self, *args, **kwargs):
        if RPC.RPCReadyOk("DNS") and RPC.RPCReadyOk("secDNS"):
            configs = RPC.fn_call("DNS", "/config", "config_get")
            rs = configs

            ip4_cfg = rs["ipv4"]
            ip6_cfg = rs["ipv6"]

            ip4_enable_auto = bool(int(ip4_cfg["enable_auto"]))
            ip6_enable_auto = bool(int(ip6_cfg["enable_auto"]))

            ip4_cfg["enable_auto"] = ip4_enable_auto
            ip6_cfg["enbale_auto"] = ip6_enable_auto

            pub = rs["public"]
            pub["enable_ipv6_dns_drop"] = bool(int(pub["enable_ipv6_dns_drop"]))
            pub["enable_dns_no_system_drop"] = bool(int(pub["enable_dns_no_system_drop"]))

            uri = "dns-server.html"

            secDNS_configs = RPC.fn_call("secDNS", "/config", "config_get")
            public = secDNS_configs.get("public", {})
            enable = public.get("enable", 0)

            try:
                enable = int(enable)
            except ValueError:
                enable = 0

            rs['enable_edns'] = bool(enable)

        else:
            uri = "no-proc.html"
            rs = {"proc_name": "DNS or secDNS"}

        return True, uri, rs
