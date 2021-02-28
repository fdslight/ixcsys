#!/usr/bin/env python3
# 初始化配置工具

import os, sys

sys_dir = os.path.dirname(os.path.abspath(__file__))

sys.path.append(sys_dir)

import pywind.lib.configfile as cfg
import pywind.lib.netutils as netutils

helper = """if wan | lan  hwaddr your_hardware_addresss
if wan | lan  dev your_network_card_name
user reset
system reset
help"""


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
        if seq[0] not in ("dev", "hwaddr",):
            print(helper)
            return

        if seq[0] == "dev":
            self.lan_do_dev(seq[1])

        if seq[0] == "hwaddr":
            self.lan_do_hwaddr(seq[1])

    def lan_do_dev(self, devname: str):
        fpath = "%s/ixc_configs/router/lan.ini" % sys_dir

        conf = cfg.ini_parse_from_file(fpath)
        conf["if_config"]["phy_ifname"] = devname

        cfg.save_to_ini(conf, fpath)

    def lan_do_hwaddr(self, hwaddr: str):
        fpath = "%s/ixc_configs/router/lan.ini" % sys_dir

        conf = cfg.ini_parse_from_file(fpath)
        conf["if_config"]["hwaddr"] = hwaddr

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
