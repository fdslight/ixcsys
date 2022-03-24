#!/usr/bin/env python3
import json, os
import ixc_syslib.pylib.RPCClient as RPC
import ixc_syslib.web.ui_widget as ui_widget
import ixc_syscore.sysadm.pylib.network_shift as network_shift


class widget(ui_widget.widget):
    def get_network_shift_conf(self):
        fpath = "%s/network_shift.json" % self.my_conf_dir

        if not os.path.isfile(fpath):
            o = {
                "enable": False,
                "temp_device": "",
                "check_host": ""
            }
            return o
        with open(fpath, "r") as f: s = f.read()
        f.close()

        return json.loads(s)

    def handle(self, *args, **kwargs):
        _type = self.get_argument("type", default="wan")
        if _type not in ("wan", "lan",): _type = "wan"

        manage_addr = ""
        mask = ""

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


        return True, "system-network.html", {"if_name": if_name, "hwaddr": hwaddr, "manage_addr": manage_addr,
                                             "mask": mask, "ip_addr": ip_addr,
                                             "net_devices": network_shift.get_available_net_devices(),
                                             }
