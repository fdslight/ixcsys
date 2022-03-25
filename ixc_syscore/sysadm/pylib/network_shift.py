#!/usr/bin/env python3
import ixc_syslib.pylib.RPCClient as RPC
import ixc_syslib.pylib.osnet as osnet
import pywind.lib.netutils as netutils
import socket, time


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


class network(object):
    __https_host = None
    # 失败计数
    __fail_count = None
    __time = None

    def __init__(self):
        self.__fail_count = 0
        self.__time = time.time()

    def __test_network(self, https_host: str):
        self.__time = time.time()
        if netutils.is_ipv6_address(https_host):
            af = socket.AF_INET6
        else:
            af = socket.AF_INET

        s = socket.socket(af, socket.SOCK_STREAM)
        s.settimeout(3)

        try:
            s.connect((self.__https_host, 443))
        except:
            self.__fail_count += 1
            s.close()
            return
        s.close()
        self.__fail_count = 0

    def network_ok(self, https_host: str):
        t = time.time()
        # 每隔60s测试一次网络
        if t - self.__time < 60: return True
        self.__test_network(https_host)
        if self.__fail_count >= 3: return False
        return True
