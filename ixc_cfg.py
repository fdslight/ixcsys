#!/usr/bin/env python3
# 初始化配置工具

import os, sys

sys_dir = os.path.dirname(os.path.abspath(__file__))

sys.path.append(sys_dir)

import pywind.lib.configfile as cfg
import pywind.lib.netutils as netutils

helper = """if wan | lan  hwaddr your_hardware_addresss
if wan dev your_network_card_name
if lan dev your_network_card_name1[,your_network_card_name2,your_network_card_name3,...]
if lan manage_addr your_manage_ip_addr
if lan ip_addr your_lan_gateway_addr
if lan mask mask
user reset
system reset
help"""


def get_if_net_devices():
    if_names = os.listdir("/sys/class/net")
    results = []
    for if_name in if_names:
        # 去除无效的网卡
        if if_name == "lo": continue
        results.append(if_name)
    return results


class ifconfig(object):
    def __init__(self, seq: list):
        if len(seq) < 2:
            print(helper)
            return
        if seq[0] not in ("wan", "lan",):
            print(helper)
            return

        if seq[0] == "wan":
            self.wan_do(seq[1:])
        else:
            self.lan_do(seq[1:])

    def lan_do(self, seq: list):
        if len(seq) < 2:
            print(helper)
            return
        if seq[0] not in ("dev", "hwaddr", "manage_addr", "ip_addr", "mask",):
            print(helper)
            return

        if seq[0] == "dev":
            self.lan_do_dev(seq[1])

        if seq[0] == "hwaddr":
            self.lan_do_hwaddr(seq[1])

        if seq[0] == "manage_addr":
            self.lan_do_manage_addr(seq[1])

        if seq[0] == "ip_addr":
            self.lan_do_ipaddr(seq[1])

        if seq[0] == "mask":
            self.lan_do_mask(seq[1])

    def lan_do_dev(self, devnames: str):
        _list = devnames.split(",")
        devname_list = []
        for devname in _list:
            if not devname: continue
            if devname not in get_if_net_devices():
                print("ERROR:not found system network card %s for LAN" % devname)
                return
            devname_list.append(devname)
        ''''''

        fpath = "%s/ixc_configs/router/lan.ini" % sys_dir

        conf = cfg.ini_parse_from_file(fpath)
        conf["if_config"]["phy_ifname"] = ",".join(devname_list)

        cfg.save_to_ini(conf, fpath)

    def lan_do_hwaddr(self, hwaddr: str):
        fpath = "%s/ixc_configs/router/lan.ini" % sys_dir

        conf = cfg.ini_parse_from_file(fpath)
        conf["if_config"]["hwaddr"] = hwaddr

        cfg.save_to_ini(conf, fpath)

    def lan_do_manage_addr(self, manage_addr: str):
        if not netutils.is_ipv4_address(manage_addr):
            print("ERROR:manage address %s not is a IPv4 address" % manage_addr)
            return

        fpath = "%s/ixc_configs/router/lan.ini" % sys_dir

        conf = cfg.ini_parse_from_file(fpath)
        conf["if_config"]["manage_addr"] = manage_addr

        cfg.save_to_ini(conf, fpath)

    def lan_do_ipaddr(self, addr: str):
        if not netutils.is_ipv4_address(addr):
            print("ERROR:LAN gateway address %s not is a IPv4 address" % addr)
            return

        fpath = "%s/ixc_configs/router/lan.ini" % sys_dir

        conf = cfg.ini_parse_from_file(fpath)
        conf["if_config"]["ip_addr"] = addr

        cfg.save_to_ini(conf, fpath)

    def lan_do_mask(self, mask: str):
        if not netutils.is_ipv4_address(mask):
            print("ERROR:LAN gateway MASK %s not is a IPv4 address" % mask)
            return

        if not netutils.is_mask(mask):
            print("ERROR:LAN IP MASK %s not is a valid mask" % mask)
            return

        fpath = "%s/ixc_configs/router/lan.ini" % sys_dir

        conf = cfg.ini_parse_from_file(fpath)
        conf["if_config"]["mask"] = mask

        cfg.save_to_ini(conf, fpath)

    def wan_do(self, seq: list):
        if len(seq) < 2:
            print(helper)
            return
        if seq[0] not in ("dev", "hwaddr",):
            print(helper)
            return

        if seq[0] == "dev":
            self.wan_do_dev(seq[1])
        else:
            self.wan_do_hwaddr(seq[1])

    def wan_do_dev(self, devname: str):
        if devname not in get_if_net_devices():
            print("ERROR:not found system network card %s for WAN" % devname)
            return

        fpath = "%s/ixc_configs/router/wan.ini" % sys_dir

        conf = cfg.ini_parse_from_file(fpath)
        conf["public"]["phy_ifname"] = devname

        cfg.save_to_ini(conf, fpath)

    def wan_do_hwaddr(self, hwaddr: str):
        fpath = "%s/ixc_configs/router/wan.ini" % sys_dir

        conf = cfg.ini_parse_from_file(fpath)
        conf["public"]["hwaddr"] = hwaddr

        cfg.save_to_ini(conf, fpath)


class user(object):
    def __init__(self, seq: list):
        if len(seq) != 1:
            print(helper)
            return

        action = seq[0]
        if action != "reset":
            print(helper)
            return
        self.do_reset()

    def do_reset(self):
        src = "%s/ixc_configs_bak/sysadm/user.json" % sys_dir
        dst = "%s/ixc_configs/sysadm" % sys_dir
        os.system("cp -v %s %s" % (src, dst,))


class system(object):
    def __init__(self, seq: list):
        if len(seq) != 1:
            print(helper)
            return

        action = seq[0]
        if action != "reset":
            print(helper)
            return
        self.do_reset()

    def do_reset(self):
        src = "%s/ixc_configs_bak/sysadm/user.json" % sys_dir
        dst = "%s/ixc_configs" % sys_dir
        os.system("cp -rv %s %s" % (src, dst,))


def main():
    if len(sys.argv) < 2:
        print(helper)
        return

    if sys.argv[1] == "help":
        print(helper)
        return

    if len(sys.argv) < 3:
        print(helper)
        return

    if sys.argv[1] not in ("if", "user", "system", "help",):
        print(helper)
        return

    if sys.argv[1] == "if":
        ifconfig(sys.argv[2:])

    if sys.argv[1] == "user":
        user(sys.argv[2:])

    if sys.argv[1] == "system":
        system(sys.argv[2:])


if __name__ == '__main__': main()
