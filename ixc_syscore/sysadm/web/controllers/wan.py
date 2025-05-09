#!/usr/bin/env python3

import ixc_syscore.sysadm.web.controllers.controller as base_controller
import ixc_syslib.pylib.RPCClient as RPC

import pywind.lib.netutils as netutils


class controller(base_controller.BaseController):
    def myinit(self):
        self.request.set_allow_methods(["POST"])
        return True

    def pppoe_host_uniq_check_ok(self, host_uniq: str):
        if len(host_uniq) % 2 != 0:
            host_uniq = "0" + host_uniq
        i = 0
        size = len(host_uniq)
        while i < size:
            x = "0x" + host_uniq[i:i + 2]
            i = i + 2
            try:
                int(x, 16)
            except ValueError:
                return False
            ''''''
        return True

    def handle_pppoe(self):
        action = self.request.get_argument('action', is_qs=False, is_seq=False)
        if action == "force-re-dial":
            RPC.fn_call("router", "/config", "pppoe_force_re_dial")
            self.json_resp(False, "PPPoE强制拨号成功")
            return
        ''''''
        username = self.request.get_argument("username", is_seq=False, is_qs=False)
        passwd = self.request.get_argument("passwd", is_seq=False, is_qs=False)
        s_heartbeat_enable = self.request.get_argument("heartbeat", is_qs=False, is_seq=False)

        chk_net_host = self.request.get_argument("chk-net-host", is_seq=False, is_qs=False)
        chk_net_port = self.request.get_argument("chk-net-port", is_seq=False, is_qs=False)
        s_chk_net_enable = self.request.get_argument("chk-net-enable", is_seq=False, is_qs=False)
        service_name = self.request.get_argument("service-name", is_qs=False, is_seq=False)
        host_uniq = self.request.get_argument("host-uniq", is_qs=False, is_seq=False)

        if not s_heartbeat_enable:
            heartbeat_enable = False
        else:
            heartbeat_enable = True

        if s_chk_net_enable:
            chk_net_enable = True
        else:
            chk_net_enable = False

        if not username or not passwd:
            self.json_resp(True, "用户名或者密码为空")
            return

        if not service_name:
            service_name = ""
        if not host_uniq:
            host_uniq = ""

        if not chk_net_port:
            chk_net_port = ""

        if host_uniq:
            if host_uniq[0:2].lower() != "0x":
                self.json_resp(True, "错误的pppoe host uniq 值")
                return
            if len(host_uniq) == 2:
                self.json_resp(True, "错误的pppoe host uniq 值")
                return
            host_uniq = host_uniq[2:]
            if not self.pppoe_host_uniq_check_ok(host_uniq):
                self.json_resp(True, "错误的pppoe host uniq 值")
                return
            if len(host_uniq) > 128:
                self.json_resp(True, "pppoe host uniq长度过长,最大支持64字节")
                return
            ''''''
        if len(service_name) > 64:
            self.json_resp(True, "pppoe host uniq长度过长,最大支持64个UTF-8长度")
            return

        if chk_net_enable:
            try:
                chk_net_port = int(chk_net_port)
            except ValueError:
                self.json_resp(True, "错误的网络探测主机端口号")
                return
            if chk_net_port < 1 or chk_net_port > 65535:
                self.json_resp(True, "错误的网络探测主机端口号")
                return
            if not netutils.is_ipv4_address(chk_net_host) and not netutils.is_ipv6_address(chk_net_host):
                self.json_resp(True, "主机必须为IPv4地址或者IPv6地址")
                return
            ''''''
        else:
            # 未开启那么不保存配置
            chk_net_host = ""
            chk_net_port = 0
            ''''''

        RPC.fn_call("router", "/config", "wan_pppoe_chk_net_info_set", chk_net_host, chk_net_port, chk_net_enable)

        RPC.fn_call("router", "/config", "pppoe_set", username, passwd, heartbeat=heartbeat_enable, host_uniq=host_uniq,
                    service_name=service_name)
        RPC.fn_call("router", "/config", "internet_type_set", "pppoe")
        RPC.fn_call("router", "/config", "config_save")

        self.json_resp(False, {})

    def handle_static_ip(self):
        ip = self.request.get_argument("ip", is_qs=False, is_seq=False)
        mask = self.request.get_argument("mask", is_qs=False, is_seq=False)
        gw = self.request.get_argument("gateway", is_qs=False, is_seq=False)

        if not ip:
            self.json_resp(True, self.LA("empty IP address"))
            return

        if not mask:
            self.json_resp(True, self.LA("empty mask value"))
            return

        if not netutils.is_mask(mask):
            self.json_resp(True, self.LA("wrong mask format"))
            return

        if not gw:
            self.json_resp(True, self.LA("empty gateway address"))
            return

        if not netutils.is_ipv4_address(ip):
            self.json_resp(True, self.LA("wrong IP address format"))
            return

        if not netutils.is_ipv4_address(mask):
            self.json_resp(True, self.LA("wrong mask format"))
            return

        if not netutils.is_ipv4_address(gw):
            self.json_resp(True, self.LA("wrong gateway address format"))
            return

        prefix = netutils.mask_to_prefix(mask, is_ipv6=False)
        if not netutils.is_same_network(ip, gw, prefix, is_ipv6=False):
            self.json_resp(True, self.LA("there is different network for ip address and gateway"))
            return

        RPC.fn_call("router", "/config", "wan_addr_set", ip, mask, gw)
        RPC.fn_call("router", "/config", "internet_type_set", "static-ip")
        RPC.fn_call("router", "/config", "config_save")

        self.json_resp(False, {})

    def handle_dhcp(self):
        s = self.request.get_argument("positive_heartbeat", is_qs=False, is_seq=False)

        if not s:
            b = False
        else:
            b = True

        RPC.fn_call("router", "/config", "internet_type_set", "dhcp")
        RPC.fn_call("router", "/config", "dhcp_positive_heartbeat_set", positive_heartbeat=b)
        RPC.fn_call("router", "/config", "config_save")

        self.json_resp(False, {})

    def dhcp_client_reset(self):
        RPC.fn_call("DHCP", "/dhcp_client", "reset")
        self.json_resp(False, {})

    def handle(self):
        _type = self.request.get_argument("type", is_qs=True, is_seq=False)
        if _type not in ("pppoe", "dhcp", "static-ip", "dhcp-client-reset"):
            self.json_resp(True, "wrong request internet type")
            return

        if _type == "pppoe":
            self.handle_pppoe()
            return
        if _type == "dhcp":
            self.handle_dhcp()
            return
        if _type == "static-ip":
            self.handle_static_ip()
            return

        self.dhcp_client_reset()
