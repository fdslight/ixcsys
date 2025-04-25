#!/usr/bin/env python3
import ixc_syslib.web.ui_widget as ui_widget
import ixc_syslib.pylib.RPCClient as RPC


class widget(ui_widget.widget):

    def handle(self, *args, **kwargs):
        _type = self.get_argument("type", default="pppoe", is_qs=True, is_seq=False)

        if _type not in ("pppoe", "dhcp", "static-ip",): _type = "dhcp"
        kwargs = {}
        configs = RPC.fn_call("router", "/config", "wan_config_get")
        router_configs = RPC.fn_call("router", "/config", "router_config_get")

        pppoe_net_monitor = router_configs['pppoe_net_monitor']

        if _type == "pppoe":
            kwargs = configs["pppoe"]
            kwargs["heartbeat"] = bool(int(kwargs["heartbeat"]))
            kwargs['chk_net_enable'] = bool(int(pppoe_net_monitor['enable']))
            kwargs['chk_net_host'] = pppoe_net_monitor['host']
            kwargs['chk_net_port'] = pppoe_net_monitor['port']
            kwargs['service_name'] = kwargs.get('service_name', '')
            host_uniq = kwargs.get('host_uniq', '')

            if host_uniq:
                kwargs['host_uniq'] = "0x" + host_uniq
            else:
                kwargs['host_uniq'] = host_uniq

        if _type == "static-ip":
            kwargs = configs["ipv4"]

        if _type == "dhcp":
            kwargs = configs["dhcp"]
            kwargs["positive_heartbeat"] = bool(int(kwargs["positive_heartbeat"]))

        return True, "wan.html", kwargs
