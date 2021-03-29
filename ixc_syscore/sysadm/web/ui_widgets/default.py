#!/usr/bin/env python3
import platform, os, sys
import ixc_syslib.web.ui_widget as ui_widget
import ixc_syslib.pylib.RPCClient as RPC


class widget(ui_widget.widget):
    def get_system_info(self):
        sys_info = {
            "os_type": sys.platform,
            "arch": platform.machine(),
            "cpu_count": os.cpu_count(),
            "ixcsys_version": "1.0.0-b1"
        }
        return sys_info

    def handle(self, *args, **kwargs):
        uri = "default.html"
        dic = {}

        wan_configs = RPC.fn_call("router", "/config", "wan_config_get")
        pub = wan_configs["public"]
        dic["internet_type"] = pub["internet_type"]

        # wan_ip_info = RPC.fn_call("router", "/runtime", "get_wan_ipaddr_info", is_ipv6=False)

        nameservers = RPC.fn_call("DNS", "/config", "get_nameservers", is_ipv6=False)
        nameservers6 = RPC.fn_call("DNS", "/config", "get_nameservers", is_ipv6=True)

        dic["nameservers"] = nameservers
        dic["nameservers6"] = nameservers6

        wan_ipinfo = RPC.fn_call("router", "/runtime", "get_wan_ipaddr_info", is_ipv6=False)

        if not wan_ipinfo:
            dic["wan_ip"] = ""
            dic["wan_prefix"] = ""
        else:
            dic["wan_ip"] = wan_ipinfo[0]
            dic["wan_prefix"] = wan_ipinfo[1]

        dic["cpu_arch"] = platform.machine()
        dic["cpu_count"] = os.cpu_count()
        dic["version"] = "1.0.0"

        return True, uri, dic
