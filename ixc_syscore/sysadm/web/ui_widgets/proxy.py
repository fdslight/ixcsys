#!/usr/bin/env python3
import ixc_syslib.web.ui_widget as ui_widget
import ixc_syslib.pylib.RPCClient as RPC
import ixc_syslib.pylib.logging as logging


class widget(ui_widget.widget):
    def convert_conn_cfg(self, configs: dict):
        conn = configs["connection"]
        tunnel_over_https = configs["tunnel_over_https"]

        conn["enable_ipv6"] = bool(int(conn["enable_ipv6"]))
        conn["udp_tunnel_redundancy"] = bool(int(conn["udp_tunnel_redundancy"]))
        conn["tunnel_over_https"] = bool(int(conn["tunnel_over_https"]))
        conn["enable"] = bool(int(conn["enable"]))

        tunnel_over_https["enable_https_sni"] = bool(int(tunnel_over_https["enable_https_sni"]))
        tunnel_over_https["strict_https"] = bool(int(tunnel_over_https["strict_https"]))

        src_filter = configs["src_filter"]
        src_filter["enable"] = bool(int(src_filter["enable"]))

        return configs

    def handle(self, *args, **kwargs):
        _type = self.get_argument("type", default="conn", is_qs=True, is_seq=False)

        if _type not in ("conn", "dns", "pass-ip", "proxy-ip", "racs",): _type = "conn"

        if RPC.RPCReadyOk("proxy"):
            configs = RPC.fn_call("proxy", "/config", "config_get", _type)
            crypto_modules = RPC.fn_call("proxy", "/config", "get_crypto_modules")

            if _type == "conn":
                configs = self.convert_conn_cfg(configs)
                configs["crypto_modules"] = crypto_modules

            uri = "proxy.html"
        else:
            configs = {}
            uri = "no-proc.html"
            configs = {"proc_name": "proxy"}

        return True, uri, configs
