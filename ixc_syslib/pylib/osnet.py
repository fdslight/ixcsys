#!/usr/bin/env python3

import os


def get_if_net_devices():
    """获取系统的网卡设备
    """
    if_names = os.listdir("/sys/class/net")
    results = []
    for if_name in if_names:
        # 去除无效的网卡
        if if_name == "lo": continue
        if if_name[0:3] == "ixc": continue
        # 去除wiregurad网卡
        if if_name[0:2] == "wg": continue
        # 丢弃无线网卡
        if if_name[0:2] == "wl": continue
        # 丢弃tap网卡
        if if_name[0:3] == "tap": continue
        # 丢弃tun网卡
        if if_name[0:3] == "tun": continue
        results.append(if_name)

    return results
