#!/usr/bin/env python3
import json, os, subprocess
import ixc_syslib.pylib.RPCClient as RPC
import ixc_syslib.web.ui_widget as ui_widget
import ixc_syscore.sysadm.pylib.network as network


class widget(ui_widget.widget):
    def get_network_shift_conf(self):
        fpath = "%s/network_shift.json" % self.my_conf_dir

        if not os.path.isfile(fpath):
            o = {
                "enable": False,
                "device_name": "",
                "check_host": "",
                # 是否是主网络
                "is_main": False,
                "internet_type": ""
            }
            return o
        with open(fpath, "r") as f: s = f.read()
        f.close()

        return json.loads(s)

    def get_if_neg_speed(self, if_names: str):
        """获取网卡协商速度,考虑到多张网卡有逗号隔开的场景
        """
        _list = if_names.split(",")
        results = []

        for if_name in _list:
            fpath = "/sys/class/net/%s/speed" % if_name
            if not os.path.isfile(fpath):
                results.append("0Mbit/s")
            else:
                with open(fpath, "r") as f:
                    s = f.read()
                f.close()
                s = s.replace("\n", "")
                s = s.replace("\r", "")
                results.append(s + "Mbit/s")
            ''''''
        return ",".join(results)

    def handle(self, *args, **kwargs):
        _type = self.get_argument("type", default="wan")
        if _type not in ("wan", "lan", "pass",): _type = "wan"

        manage_addr = ""
        mask = ""
        avaliable_devices = network.get_available_net_devices()
        enable_pass = False
        peer_host = ""
        peer_port = ""
        pass_key = ""
        vlan_enable_pass = False
        router_config = RPC.fn_call("router", "/config", "router_config_get")
        vid = router_config['config']["vlanid_for_passdev"]
        wan_vlan_id = 0
        neg_speed = "0Mbit/s"

        if _type == "wan":
            configs = RPC.fn_call("router", "/config", "wan_config_get")
            public = configs["public"]
            vlan = configs["vlan"]
            if_name = public["phy_ifname"]
            hwaddr = public["hwaddr"]
            # 避免模板找不到变量报错
            ip_addr = ""
            ip4_mtu = public.get("ip4_mtu", 1500)
            try:
                if int(vlan['enable_pass']) != 0:
                    vlan_enable_pass = True
            except ValueError:
                pass

            try:
                wan_vlan_id = int(vlan['vlan_id'])
            except ValueError:
                pass
            neg_speed = self.get_if_neg_speed(if_name)

        elif _type == "pass":
            configs = RPC.fn_call("router", "/config", "lan_config_get")
            config = configs["passthrough"]
            if_name = config['if_name']
            if if_name not in avaliable_devices:
                if_name = ''
            enable_pass = bool(int(config['enable']))
            hwaddr = ""
            manage_addr = ""
            mask = ""
            ip_addr = ""
            ip4_mtu = ""
        else:
            configs = RPC.fn_call("router", "/config", "lan_config_get")
            if_config = configs["if_config"]
            if_name = if_config["phy_ifname"]
            hwaddr = if_config["hwaddr"]
            manage_addr = if_config["manage_addr"]
            mask = if_config["mask"]
            ip_addr = if_config["ip_addr"]
            # 避免模板找不到变量报错
            ip4_mtu = 1500
            neg_speed = self.get_if_neg_speed(if_name)

        # network_shift_conf = self.get_network_shift_conf()

        return True, "system-network.html", {"if_name": if_name, "hwaddr": hwaddr, "manage_addr": manage_addr,
                                             "mask": mask, "ip_addr": ip_addr,
                                             "ip4_mtu": ip4_mtu,
                                             "net_devices": avaliable_devices,
                                             "enable_pass": enable_pass,
                                             "vlan_id": vid,
                                             "vlan_enable_pass": vlan_enable_pass,
                                             "wan_vlan_id": wan_vlan_id,
                                             "neg_speed": neg_speed,
                                             }
