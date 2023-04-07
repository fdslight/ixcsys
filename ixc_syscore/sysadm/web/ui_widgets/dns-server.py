#!/usr/bin/env python3
import ixc_syslib.web.ui_widget as ui_widget
import ixc_syslib.pylib.RPCClient as RPC


class widget(ui_widget.widget):
    def handle(self, *args, **kwargs):
        if RPC.RPCReadyOk("DNS"):
            configs = RPC.fn_call("DNS", "/config", "config_get")
            rs = configs
            
            ip4_cfg=rs["ipv4"]
            ip6_cfg=rs["ipv6"]

            ip4_enable_auto=bool(int(ip4_cfg.get("enable_auto","1")))
            ip6_enable_auto=bool(int(ip6_cfg.get("enable_auto","1")))

            ip4_cfg["enable_auto"]=ip4_enable_auto
            ip6_cfg["enbale_auto"]=ip6_enable_auto

            uri = "dns-server.html"
        else:
            uri = "no-proc.html"
            rs = {"proc_name": "DNS"}

        return True, uri, rs
