#!/usr/bin/env python3
import json
import ixc_syscore.sysadm.web.controllers.controller as base_controller

import ixc_syslib.pylib.RPCClient as RPC
import pywind.lib.netutils as netutils
import ixc_syscore.sysadm.pylib.network_shift as network_shift


class controller(base_controller.BaseController):
    def myinit(self):
        self.request.set_allow_methods(["POST"])
        return True

    def handle_wan_submit(self):
        hwaddr = self.request.get_argument("hwaddr", is_seq=False, is_qs=False)
        enable_auto = self.request.get_argument("enable_auto", is_seq=False, is_qs=False)
        temp_ifname = self.request.get_argument("shift_ifname", is_seq=False, is_qs=False)
        check_host = self.request.get_argument("check_host", is_seq=False,
                                               is_qs=False)
        ip4_mtu = self.request.get_argument("ip4_mtu", is_seq=False, is_qs=False)

        if enable_auto and temp_ifname not in network_shift.get_available_net_devices():
            self.json_resp(True, "不可用的故障切换网卡")
            return

        if enable_auto:
            enable_auto = True
        else:
            enable_auto = False

        if not hwaddr:
            self.json_resp(True, "硬件地址不能为空")
            return
        if not netutils.is_hwaddr(hwaddr):
            self.json_resp(True, "错误的硬件地址格式")
            return

        if enable_auto:
            if not check_host:
                self.json_resp(True, "请设置检查网络的https服务器地址")
                return
            if netutils.is_ipv6_address(check_host):
                self.json_resp(True, "不支持IPv6地址作为检查主机")
                return
            p = check_host.find(":")
            if p >= 0:
                self.json_resp(True, "地址不能携带端口号")
                return
            ''''''
        try:
            int(ip4_mtu)
        except ValueError:
            self.json_resp(True, "错误的MTU值类型")
            return

        if ip4_mtu < 576 or ip4_mtu > 1500:
            self.json_resp(True, "MTU的取值范围为576~1500")
            return

        if not check_host: check_host = ""
        if not temp_ifname: temp_ifname = ""

        configs = RPC.fn_call("router", "/config", "lan_config_get")
        lan_hwaddr = configs["if_config"]["hwaddr"]
        if lan_hwaddr == hwaddr:
            self.json_resp(True, "WAN与LAN的地址不能相同")
            return

        o = {
            "enable": enable_auto,
            "device_name": temp_ifname,
            "check_host": check_host,
            # 是否是主网络
            "is_main": False,
            "internet_type": "dhcp"
        }

        self.save_sysadm_json_config("%s/network_shift.json" % self.my_config_dir, o)

        RPC.fn_call("router", "/config", "wan_hwaddr_set", hwaddr)
        RPC.fn_call("router", "/config", "wan_mtu_set", ip4_mtu, False)
        RPC.fn_call("router", "/config", "config_save")
        self.json_resp(False, "")

    def handle_lan_submit(self):
        hwaddr = self.request.get_argument("hwaddr", is_seq=False, is_qs=False)
        manage_addr = self.request.get_argument("manage_addr", is_seq=False, is_qs=False)
        mask = self.request.get_argument("mask", is_seq=False, is_qs=False)
        ip_addr = self.request.get_argument("ip_addr", is_seq=False, is_qs=False)

        if not hwaddr:
            self.json_resp(True, "硬件地址不能为空")
            return
        if not netutils.is_hwaddr(hwaddr):
            self.json_resp(True, "错误的硬件地址格式")
            return

        configs = RPC.fn_call("router", "/config", "wan_config_get")
        wan_hwaddr = configs["public"]["hwaddr"]
        if wan_hwaddr == hwaddr:
            self.json_resp(True, "WAN与LAN的地址不能相同")
            return

        if not manage_addr:
            self.json_resp(True, "空的管理地址")
            return
        if not mask:
            self.json_resp(True, "空的子网掩码")
            return

        if not netutils.is_ipv4_address(manage_addr):
            self.json_resp(True, "错误的管理地址格式")
            return

        if not netutils.is_mask(mask):
            self.json_resp(True, "错误的掩码格式")
            return

        if not ip_addr:
            self.json_resp(True, "空的路由器地址")
            return

        if not netutils.is_ipv4_address(ip_addr):
            self.json_resp(True, "错误的路由器地址格式")
            return

        prefix = netutils.mask_to_prefix(mask, is_ipv6=False)
        subnet_a = netutils.calc_subnet(ip_addr, prefix, is_ipv6=False)
        subnet_b = netutils.calc_subnet(manage_addr, prefix, is_ipv6=False)

        if subnet_a != subnet_b:
            self.json_resp(True, "管理地址和路由器地址不在同一个局域网内")
            return

        RPC.fn_call("router", "/config", "lan_hwaddr_set", hwaddr)
        RPC.fn_call("router", "/config", "manage_addr_set", manage_addr)
        RPC.fn_call("router", "/config", "lan_addr_set", ip_addr, mask)

        RPC.fn_call("router", "/config", "config_save")

        self.json_resp(False, "")

    def handle(self):
        _type = self.request.get_argument("type", is_qs=True, is_seq=False)
        types = [
            "lan", "wan",
        ]
        if _type not in types:
            self.json_resp(True, "unknown request type")
            return

        if _type == "lan":
            self.handle_lan_submit()
        else:
            self.handle_wan_submit()
