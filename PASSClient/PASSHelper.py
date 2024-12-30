#!/usr/bin/env python3
import os.path, sys, hashlib
import time, socket

import PASSClientRuntime

sys.path.append("%s/../" % os.path.dirname(__file__))

import ixc_syslib.pylib.osnet as osnet
import pywind.lib.netutils as netutils


class helper(object):
    __key = None
    __ifname = None
    __tapname = None
    __br_name = None
    __up_time = None
    __peer_address = None
    __peer_hostname = None
    __peer_port = None
    __runtime = None
    __debug = None
    __tap_fd = None

    def __init__(self, debug, ifname: str, host: str, key: str):
        self.__debug = debug
        self.__tapname = "ixcpass"
        self.__br_name = "ixcpassbr"
        self.__up_time = time.time()
        self.__peer_hostname = host
        self.__tap_fd = -1

        if ifname not in osnet.get_if_net_devices():
            print("ERROR: IF DEVICE NOT FOUND %s" % ifname)
            sys.exit(1)

        if netutils.is_ipv6_address(host):
            print("ERROR:not support IPv6 address %s" % host)
            sys.exit(1)

        self.__peer_address = self.get_peer_address(host)
        self.__ifname = ifname
        byte_key = key.encode()
        self.__key = hashlib.md5(byte_key).digest()
        self.__runtime = PASSClientRuntime.PASSClientRuntime()

    def start(self):
        self.__tap_fd = self.__runtime.netif_create(self.__tapname)
        if self.__tap_fd < 0:
            print("ERROR:cannot create tap device %s" % self.__tapname)
            sys.exit(1)
        self.linux_br_create(self.__br_name, [self.__ifname, self.__tapname])

        if self.__peer_address is None: return
        self.set_forward()

    def set_forward(self):
        byte_addr = socket.inet_pton(socket.AF_INET, self.__peer_address)
        self.__runtime.netpkt_forward_set(
            self.__key, byte_addr, 8964
        )

    def release(self):
        self.delete_bridge()
        if self.__tap_fd >= 0:
            self.__runtime.netif_delete()
        return

    def get_peer_address(self, hostname: str):
        if netutils.is_ipv4_address(hostname):
            return hostname
        try:
            s = socket.gethostbyname(hostname)
        except:
            return None
        return s

    def update_peer_address(self):
        s = self.get_peer_address(self.__peer_hostname)

        if s is None: return
        if s == self.__peer_address: return

        self.__peer_address = s
        self.update_peer_address()

    def check_bridge(self):
        """定期检查网卡桥接状态"""
        fd = os.popen("ip addr | grep %s | grep master" % self.__ifname)
        s = fd.read()
        fd.close()
        if not s:
            cmd = "ip link set dev %s master %s" % (self.__ifname, self.__br_name,)
            os.system(cmd)
        ''''''

    def loop(self):
        self.update_peer_address()
        self.check_bridge()

    def linux_br_create(self, br_name: str, added_bind_ifs: list):
        cmds = [
            "ip link add name %s type bridge" % br_name,
            "ip link set dev %s up" % br_name,
        ]

        for cmd in cmds: os.system(cmd)
        for if_name in added_bind_ifs:
            cmd = "ip link set dev %s master %s" % (if_name, br_name,)
            os.system(cmd)
            os.system("ip link set %s promisc on" % if_name)

    def delete_bridge(self):
        os.system("ip link set %s nomaster" % self.__tapname)
        os.system("ip link set %s nomaster" % self.__ifname)
        os.system("ip link del %s" % self.__br_name)
