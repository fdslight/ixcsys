#!/usr/bin/env python3

import ixc_syslib.pylib.RPCClient as RPC
import ixc_syslib.web.ui_widget as ui_widget
import ixc_syslib.pylib.osnet as osnet


class widget(ui_widget.widget):
    def handle(self, *args, **kwargs):
        _type = self.get_argument("type", default="wan")
        if _type not in ("wan", "lan",): _type = "wan"

        manage_addr = ""
        mask = ""

        configs = RPC.fn_call("router", "/config", "wan_config_get")
        if_wan_name = configs["public"]["phy_ifname"]

        configs = RPC.fn_call("router", "/config", "lan_config_get")
        if_lan_name = configs["if_config"]["phy_ifname"]

        if _type == "wan":
            configs = RPC.fn_call("router", "/config", "wan_config_get")
            public = configs["public"]
            if_name = public["phy_ifname"]
            hwaddr = public["hwaddr"]
            ip_addr = ""
        else:
            configs = RPC.fn_call("router", "/config", "lan_config_get")
            if_config = configs["if_config"]
            if_name = if_config["phy_ifname"]
            hwaddr = if_config["hwaddr"]
            manage_addr = if_config["manage_addr"]
            mask = if_config["mask"]
            ip_addr = if_config["ip_addr"]

        net_devices = osnet.get_if_net_devices()
        devices = []

        for if_name in net_devices:
            if if_name == if_wan_name: continue
            if if_name == if_lan_name: continue
            devices.append(if_name)

        return True, "system-network.html", {"if_name": if_name, "hwaddr": hwaddr, "manage_addr": manage_addr,
                                             "mask": mask, "ip_addr": ip_addr,
                                             "net_devices": devices}
