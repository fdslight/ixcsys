#!/usr/bin/env python3
import ixc_syslib.pylib.RPCClient as RPC
import ixc_syslib.pylib.osnet as osnet


def get_available_net_devices():
    """获取可用的网络设备
    """
    configs = RPC.fn_call("router", "/config", "wan_config_get")
    if_wan_name = configs["public"]["phy_ifname"]

    configs = RPC.fn_call("router", "/config", "lan_config_get")
    if_lan_name = configs["if_config"]["phy_ifname"]

    net_devices = osnet.get_if_net_devices()
    devices = []

    for if_name in net_devices:
        if if_name == if_wan_name: continue
        if if_name == if_lan_name: continue
        devices.append(if_name)

    return devices
