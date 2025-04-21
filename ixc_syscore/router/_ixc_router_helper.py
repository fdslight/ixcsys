#!/usr/bin/env python3
import json
import pickle, os, socket, sys, hashlib
import time
import traceback

import router

import ixc_syscore.router.pylib.pppoe as pppoe

import ixc_syslib.pylib.RPCClient as RPC
import ixc_syslib.pylib.osnet as osnet
import ixc_syslib.pylib.logging as logging
import pywind.lib.netutils as netutils
import pywind.lib.configfile as conf


class rpc(object):
    __fn_objects = None
    __helper = None

    def __init__(self, _helper):
        self.__helper = _helper

        self.__fn_objects = {
            "get_all_consts": self.get_all_consts,
            "get_wan_ipaddr_info": self.get_wan_ipaddr_info,
            "get_lan_ipaddr_info": self.get_lan_ipaddr_info,
            "add_route": self.add_route,
            "del_route": self.del_route,
            "tcp_mss_set": self.tcp_mss_set,
            "dns_drop_no_system_enable": self.dns_drop_no_system_enable,
            "set_wan_ipaddr": self.set_wan_ipaddr,
            "wan_ready_ok": self.wan_ready_ok,
            "wan_ip6_ready_ok": self.wan_ip6_ready_ok,

            "set_fwd_port": self.set_fwd_port,
            "unset_fwd_port": self.unset_fwd_port,

            "wan_config_get": self.wan_config_get,
            "lan_config_get": self.lan_config_get,
            "manage_addr_get": self.manage_addr_get,
            "wan_hwaddr_set": self.wan_hwaddr_set,
            "wan_ifname_set": self.wan_ifname_set,
            "lan_hwaddr_set": self.lan_hwaddr_set,
            "wan_mtu_set": self.wan_mtu_set,
            "wan_traffic_get": self.wan_traffic_get,
            "lan_traffic_get": self.lan_traffic_get,
            "wan_traffic_speed_get": self.wan_traffic_speed_get,
            "lan_traffic_speed_get": self.lan_traffic_speed_get,

            "manage_addr_set": self.manage_addr_set,
            "lan_addr_set": self.lan_addr_set,
            "wan_addr_set": self.wan_addr_set,
            "cur_internet_type_get": self.cur_internet_type_get,
            "internet_type_set": self.internet_type_set,
            "dhcp_positive_heartbeat_set": self.dhcp_positive_heartbeat_set,
            "lan_ipv6_pass_enable": self.lan_ipv6_pass_enable,
            "lan_static_ipv6_enable": self.lan_static_ipv6_enable,
            "lan_static_ipv6_set": self.lan_static_ipv6_set,
            "lan_ipv6_security_enable": self.lan_ipv6_security_enable,
            "passdev_set": self.passdev_set,
            "pppoe_set": self.pppoe_set,
            "pppoe_is_enabled": self.pppoe_is_enabled,
            "pppoe_dnsservers_get": self.pppoe_dnsservers_get,
            "pppoe_force_re_dial": self.pppoe_force_re_dial,
            "router_config_get": self.router_config_get,
            "port_map_add": self.port_map_add,
            "port_map_del": self.port_map_del,
            "port_map_configs_get": self.port_map_configs_get,

            "src_filter_set_ip": self.src_filter_set_ip,
            "src_filter_enable": self.src_filter_enable,
            "src_filter_set_protocols": self.src_filter_set_protocols,

            "sec_net_add_src": self.sec_net_add_src,
            "sec_net_del_src": self.sec_net_del_src,
            "sec_net_add_dst": self.sec_net_add_dst,
            "sec_net_config_get": self.sec_net_config_get,
            "net_monitor_set": self.net_monitor_set,
            "net_monitor_config_get": self.net_monitor_config_get,

            "qos_set_tunnel_first": self.qos_set_tunnel_first,
            "qos_unset_tunnel": self.qos_unset_tunnel,
            "qos_set_mpkt_first_size": self.qos_set_mpkt_first_size,
            "qos_add_first_host_hwaddr": self.qos_add_first_host_hwaddr,
            "qos_del_first_host_hwaddr": self.qos_del_first_host_hwaddr,

            "passthrough_device_add": self.passthrough_device_add,
            "passthrough_device_del": self.passthrough_device_del,
            "passthrough_set_vid_for_passdev": self.passthrough_set_vid_for_passdev,

            "cpu_num": self.cpu_num,
            "bind_cpu": self.bind_cpu,
            "router_start_time": self.router_start_time,
            "traffic_log_enable": self.traffic_log_enable,

            "icmpv6_dns_set": self.icmpv6_dns_set,
            "icmpv6_dns_unset": self.icmpv6_dns_unset,
            "icmpv6_wan_dnsserver_get": self.icmpv6_wan_dnsserver_get,

            "config_save": self.save
        }

    def call(self, fn_name: str, *args, **kwargs):
        """调用函数
        """
        if fn_name not in self.__fn_objects:
            return 0, pickle.dumps("not found function %s" % fn_name)
        fn = self.__fn_objects[fn_name]

        try:
            is_error, msg = fn(*args, **kwargs)
        except:
            expt = traceback.format_exc()
            error = "call function %s error\r\n%s" % (fn_name, expt,)
            return RPC.ERR_SYS, pickle.dumps(error)

        return is_error, pickle.dumps(msg)

    def get_all_consts(self):
        """获取所有转发数据包的flags
        :return:
        """
        values = {
            "IXC_FLAG_DHCP_CLIENT": router.IXC_FLAG_DHCP_CLIENT,
            "IXC_FLAG_DHCP_SERVER": router.IXC_FLAG_DHCP_SERVER,
            "IXC_FLAG_ARP": router.IXC_FLAG_ARP,
            "IXC_FLAG_SRC_FILTER": router.IXC_FLAG_SRC_FILTER,
            "IXC_FLAG_ROUTE_FWD": router.IXC_FLAG_ROUTE_FWD,
            "IXC_FLAG_TRAFFIC_LOG": router.IXC_FLAG_TRAFFIC_LOG,

            "IXC_NETIF_LAN": router.IXC_NETIF_LAN,
            "IXC_NETIF_WAN": router.IXC_NETIF_WAN,
            "IXC_NETIF_PASS": router.IXC_NETIF_PASS,
            "IXC_SEC_NET_ACT_DROP": router.IXC_SEC_NET_ACT_DROP,
            "IXC_SEC_NET_ACT_ACCEPT": router.IXC_SEC_NET_ACT_ACCEPT,

            "IXC_PASSTHROUGH_DEV_MAX": router.IXC_PASSTHROUGH_DEV_MAX,
        }

        return 0, values

    def get_wan_hwaddr(self):
        """获取WAN硬件地址
        :return:
        """
        wan_configs = self.__helper.wan_configs
        public = wan_configs["public"]

        return 0, (public["phy_ifname"], public["hwaddr"],)

    def get_gw_hwaddr(self):
        """获取LAN硬件地址
        :return:
        """
        if_config = self.__helper.lan_configs["if_config"]
        return 0, (if_config["phy_ifname"], if_config["hwaddr"],)

    def get_wan_ipaddr_info(self, is_ipv6=False):
        return 0, self.__helper.router.netif_get_ip(router.IXC_NETIF_WAN, is_ipv6)

    def get_lan_ipaddr_info(self, is_ipv6=False):
        return 0, self.__helper.router.netif_get_ip(router.IXC_NETIF_LAN, is_ipv6)

    def check_ipaddr_args(self, ipaddr: str, prefix: int, is_ipv6=False):
        if is_ipv6 and not netutils.is_ipv6_address(ipaddr):
            return False, "wrong IPv6 address format"
        if not is_ipv6 and not netutils.is_ipv4_address(ipaddr):
            return False, "wrong IP address format"
        try:
            prefix = int(prefix)
        except ValueError:
            return False, "wrong prefix value %s" % prefix

        if prefix < 0:
            return False, "wrong prefix value %d" % prefix
        if is_ipv6 and prefix > 128:
            return False, "wrong IPv6 prefix value %d" % prefix
        if not is_ipv6 and prefix > 32:
            return False, "wrong IP prefix value %d" % prefix

        return True, ""

    def set_gw_ipaddr(self, ipaddr: str, prefix: int, is_ipv6=False):
        """设置网关的IP地址
        """
        prefix = int(prefix)
        check_ok, err_msg = self.check_ipaddr_args(ipaddr, prefix, is_ipv6=is_ipv6)
        if not check_ok:
            return 0, (check_ok, err_msg,)

        if is_ipv6:
            fa = socket.AF_INET6
        else:
            fa = socket.AF_INET
        byte_ip = socket.inet_pton(fa, ipaddr)
        set_ok = self.__helper.router.netif_set_ip(router.IXC_NETIF_LAN, byte_ip, prefix, is_ipv6)

        return 0, (set_ok, "")

    def set_manage_ipaddr(self, ipaddr: str, is_ipv6=False, is_local=False):
        """设置管理地址
        """
        self.__helper.set_manage_ipaddr(ipaddr, is_ipv6=is_ipv6, is_local=is_local)
        return 0, None

    def get_manage_ipaddr(self):
        """获取管理地址
        """
        ipaddr = self.__helper.get_manage_addr()

        return 0, ipaddr

    def get_lan_configs(self):
        return 0, self.__helper.lan_configs

    def get_wan_configs(self):
        return 0, self.__helper.wan_configs

    def set_wan_ipaddr(self, ipaddr: str, prefix: int, is_ipv6=False):
        """设置WAN口的IP地址
        """
        check_ok, err_msg = self.check_ipaddr_args(ipaddr, int(prefix), is_ipv6=is_ipv6)
        if not check_ok:
            return 0, (check_ok, err_msg,)

        if self.__helper.router.pppoe_is_enabled():
            return 0, (False, "PPPoE is enabled,cannot set wan IP or IPv6 address")

        if is_ipv6:
            fa = socket.AF_INET6
        else:
            fa = socket.AF_INET
        byte_ip = socket.inet_pton(fa, ipaddr)
        set_ok = self.__helper.router.netif_set_ip(router.IXC_NETIF_WAN, byte_ip, prefix, is_ipv6)

        return 0, (set_ok, "")

    def add_route(self, subnet: str, prefix: int, gw: str, is_ipv6=False):
        if is_ipv6 and (not netutils.is_ipv6_address(subnet) or not netutils.is_ipv6_address(gw)):
            return 0, (False, "Wrong subnet or gateway address format for IPv6")

        if not is_ipv6 and (not netutils.is_ipv4_address(subnet) or not netutils.is_ipv4_address(gw)):
            return 0, (False, "Wrong subnet or gateway address format for IP")

        if prefix < 0:
            return 0, (False, "Wrong prefix value %d" % prefix)

        if is_ipv6 and prefix > 128:
            return 0, (False, "Wrong prefix value %d" % prefix)

        if not is_ipv6 and prefix > 32:
            return 0, (False, "Wrong prefix value %d" % prefix)

        if is_ipv6:
            fa = socket.AF_INET6
        else:
            fa = socket.AF_INET

        byte_subnet = socket.inet_pton(fa, subnet)
        byte_gw = socket.inet_pton(fa, gw)

        rs = self.__helper.router.route_add(byte_subnet, prefix, byte_gw, is_ipv6)

        return 0, (rs, "")

    def del_route(self, subnet: str, prefix: int, is_ipv6=False):
        ok, mesg = self.check_ipaddr_args(subnet, prefix, is_ipv6=is_ipv6)

        if not ok: return 0, (ok, mesg)

        if is_ipv6:
            fa = socket.AF_INET6
        else:
            fa = socket.AF_INET

        byte_subnet = socket.inet_pton(fa, subnet)
        self.__helper.router.route_del(byte_subnet, prefix, is_ipv6)

        return 0, (True, "")

    def tcp_mss_set(self, tcp_mss, is_ipv6=False):
        if tcp_mss != 0:
            if is_ipv6:
                if tcp_mss < 516 or tcp_mss > 1440: return 0, False
            else:
                if tcp_mss < 536 or tcp_mss > 1460: return 0, False
            ''''''
        if is_ipv6:
            self.__helper.router_configs["config"]["ip6_tcp_mss"] = tcp_mss
        else:
            self.__helper.router_configs["config"]["ip_tcp_mss"] = tcp_mss

        self.__helper.save_router_configs()

        return 0, self.__helper.router.route_tcp_mss_set(tcp_mss, is_ipv6)

    def dns_drop_no_system_enable(self, enable: bool, is_ipv6=False):
        return 0, self.__helper.router.dns_drop_no_system_enable(enable, is_ipv6)

    def pppoe_is_enabled(self):
        is_enabled = self.__helper.router.pppoe_is_enabled()

        return 0, is_enabled

    def wan_ready_ok(self):
        return 0, self.__helper.router.wan_ready_ok()

    def wan_ip6_ready_ok(self):
        return 0, self.__helper.router.wan_ip6_ready_ok()

    def set_fwd_port(self, flags: int, _id: bytes, fwd_port: int, address="127.0.0.1"):
        if not isinstance(_id, bytes):
            return 0, (False, "Wrong _id data type")
        if len(_id) != 16:
            return 0, (False, "Wrong _id length")
        try:
            fwd_port = int(fwd_port)
        except ValueError:
            return 0, (False, "Wrong fwd_port data type")

        if fwd_port > 0xfffe or fwd_port < 1:
            return 0, (False, "Wrong fwd_port value")

        try:
            flags = int(flags)
        except ValueError:
            return RPC.ERR_ARGS, "wrong flags value type"

        if netutils.is_ipv6_address(address):
            return RPC.ERR_ARGS, "wrong ip address value"

        byte_ip = socket.inet_pton(socket.AF_INET, address)

        rs = self.__helper.router.netpkt_forward_set(_id, byte_ip, fwd_port, flags)

        return 0, (rs, "")

    def unset_fwd_port(self, flags: int):
        try:
            flags = int(flags)
        except ValueError:
            return RPC.ERR_ARGS, "wrong argument type"
        self.__helper.router.netpkt_forward_disable(flags)
        return 0, None

    def wan_config_get(self):
        return 0, self.__helper.wan_configs

    def lan_config_get(self):
        return 0, self.__helper.lan_configs

    def manage_addr_get(self):
        lan_configs = self.__helper.lan_configs

        return 0, lan_configs["if_config"]["manage_addr"]

    def wan_hwaddr_set(self, hwaddr: str):
        if not netutils.is_hwaddr(hwaddr):
            return RPC.ERR_ARGS, "wrong hwaddr format"

        configs = self.__helper.wan_configs
        configs["public"]["hwaddr"] = hwaddr

        return 0, None

    def wan_ifname_set(self, ifname: str):
        configs = self.__helper.wan_configs
        configs["public"]["phy_ifname"] = ifname

        return 0, None

    def lan_hwaddr_set(self, hwaddr: str):
        lan_configs = self.__helper.lan_configs
        lan_configs["if_config"]["hwaddr"] = hwaddr

        return 0, None

    def wan_mtu_set(self, mtu: int, is_ipv6: bool):
        wan_configs = self.__helper.wan_configs
        public = wan_configs["public"]
        if is_ipv6:
            public["ip6_mtu"] = mtu
        else:
            public["ip4_mtu"] = mtu

        return 0, None

    def wan_traffic_get(self):
        traffic = self.__helper.router.netif_traffic_get(router.IXC_NETIF_WAN)

        return 0, traffic

    def lan_traffic_get(self):
        traffic = self.__helper.router.netif_traffic_get(router.IXC_NETIF_LAN)

        return 0, traffic

    def wan_traffic_speed_get(self):
        speed_info = self.__helper.router.netif_traffic_speed_get(router.IXC_NETIF_WAN)
        return 0, speed_info

    def lan_traffic_speed_get(self):
        speed_info = self.__helper.router.netif_traffic_speed_get(router.IXC_NETIF_LAN)
        return 0, speed_info

    def manage_addr_set(self, ip: str, is_ipv6=False):
        # 对IPv6地址进行特殊处理
        if is_ipv6:
            self.__helper.router.g_manage_addr_set(ip, True)
            return 0, None

        lan_configs = self.__helper.lan_configs
        lan_configs["if_config"]["manage_addr"] = ip

        return 0, None

    def lan_addr_set(self, ip: str, mask: str):
        lan_configs = self.__helper.lan_configs

        lan_configs["if_config"]["ip_addr"] = ip
        lan_configs["if_config"]["mask"] = mask

        return 0, None

    def cur_internet_type_get(self):
        """获取当前internet上网方式
        """
        wan_configs = self.__helper.wan_configs
        public = wan_configs["public"]

        return 0, public["internet_type"]

    def pppoe_set(self, username: str, passwd: str, heartbeat=False):
        if not username or not passwd:
            return RPC.ERR_ARGS, "empty username or password"
        configs = self.__helper.wan_configs
        pppoe = configs["pppoe"]

        pppoe["user"] = username
        pppoe["passwd"] = passwd

        if heartbeat:
            pppoe["heartbeat"] = 1
        else:
            pppoe["heartbeat"] = 0

        return 0, None

    def pppoe_dnsservers_get(self):
        return 0, self.__helper.pppoe_dnsservers

    def pppoe_force_re_dial(self):
        return 0, self.__helper.pppoe_force_re_dial()

    def internet_type_set(self, _type: str):
        types = (
            "pppoe", "dhcp", "static-ip",
        )
        if _type not in types:
            return RPC.ERR_ARGS, "wrong internet type value,there is pppoe,dhcp or static-ip"

        public = self.__helper.wan_configs["public"]
        public["internet_type"] = _type

        return 0, None

    def wan_addr_set(self, ip: str, mask: str, gw: str):
        if not netutils.is_ipv4_address(ip) or not netutils.is_mask(mask) or not netutils.is_ipv4_address(gw):
            return RPC.ERR_ARGS, "wrong argument value format"

        prefix = netutils.mask_to_prefix(mask, is_ipv6=False)
        if not netutils.is_same_network(ip, gw, prefix, is_ipv6=False):
            return RPC.ERR_ARGS, "wrong argument value"

        ipv4 = self.__helper.wan_configs["ipv4"]
        ipv4["address"] = ip
        ipv4["mask"] = mask
        ipv4["default_gw"] = gw

        return 0, None

    def lan_static_ipv6_set(self, subnet: str, prefix: int):
        if not netutils.is_ipv6_address(subnet):
            return RPC.ERR_ARGS, "wrong IPv6 addres value"
        try:
            int(prefix)
        except ValueError:
            return RPC.ERR_ARGS, "wrong prefix value type"

        prefix = int(prefix)
        if prefix < 48 or prefix > 64:
            return RPC.ERR_ARGS, "prefix value must be 48 to 64"

        configs = self.__helper.lan_configs["if_config"]
        configs["ip6_addr"] = "%s/%s" % (subnet, prefix,)

        return 0, None

    def lan_static_ipv6_enable(self, enable: bool):
        """是否开启静态IPv6地址
        """
        configs = self.__helper.lan_configs["if_config"]
        if enable:
            configs["enable_static_ipv6"] = 1
        else:
            configs["enable_static_ipv6"] = 0

        return 0, None

    def lan_ipv6_pass_enable(self, enable: bool):
        configs = self.__helper.lan_configs["if_config"]
        if enable:
            configs["enable_ipv6_pass"] = 1
        else:
            configs["enable_ipv6_pass"] = 0

        return 0, None

    def lan_ipv6_security_enable(self, enable: bool):
        configs = self.__helper.lan_configs["if_config"]
        if enable:
            configs["enable_ipv6_security"] = 1
        else:
            configs["enable_ipv6_security"] = 0

        return 0, None

    def passdev_set(self, config: dict):
        self.__helper.passdev_set(config)
        return 0, None

    def dhcp_positive_heartbeat_set(self, positive_heartbeat=False):
        dhcp = self.__helper.wan_configs["dhcp"]
        if positive_heartbeat:
            dhcp["positive_heartbeat"] = 1
        else:
            dhcp["positive_heartbeat"] = 0

        return 0, None

    def router_config_get(self):
        configs = self.__helper.router_configs

        return 0, configs

    def save(self):
        self.__helper.save_wan_configs()
        self.__helper.save_lan_configs()
        self.__helper.save_router_configs()
        self.__helper.save_net_monitor_configs()
        self.__helper.save_sec_net_configs()

        return 0, None

    def port_map_add(self, protocol: int, port: int, address: str, alias_name: str):
        """端口映射添加
        :param protocol:
        :param port:
        :param address:
        :param alias_name:映射名
        :return:
        """
        if protocol not in (6, 17, 136,):
            return RPC.ERR_ARGS, "wrong protocol number value %s" % protocol
        if not netutils.is_port_number(port):
            return RPC.ERR_ARGS, "wrong port number value %s" % port

        if not netutils.is_ipv4_address(address):
            return RPC.ERR_ARGS, "wrong address value %s" % address

        return 0, self.__helper.port_map_add(protocol, port, address, alias_name)

    def port_map_del(self, protocol: int, port: int):
        if protocol not in (6, 17, 136,):
            return RPC.ERR_ARGS, "wrong protocol number value %s" % protocol
        if not netutils.is_port_number(port):
            return RPC.ERR_ARGS, "wrong port number value %s" % port

        return 0, self.__helper.port_map_del(protocol, port)

    def port_map_configs_get(self):
        return 0, self.__helper.port_map_configs

    def src_filter_set_ip(self, ip: str, prefix: int, is_ipv6=False):
        if is_ipv6:
            byte_addr = socket.inet_pton(socket.AF_INET6, ip)
        else:
            byte_addr = socket.inet_pton(socket.AF_INET, ip)

        return 0, self.__helper.router.src_filter_set_ip(byte_addr, prefix, is_ipv6);

    def src_filter_enable(self, enable: bool):
        return 0, self.__helper.router.src_filter_enable(enable)

    def src_filter_set_protocols(self, protocol: str):
        seq = list(bytes(0xff))
        if protocol == "UDP" or protocol == "ALL":
            seq[17] = 0xff
        if protocol == "TCP" or protocol == "ALL":
            seq[6] = 0xff
        if protocol == "UDPLite" or protocol == "ALL":
            seq[136] = 0xff

        byte_data = bytes(seq)

        return 0, self.__helper.router.src_filter_set_protocols(byte_data)

    def sec_net_add_src(self, hwaddr: str, action: str):
        if not netutils.is_hwaddr(hwaddr):
            return RPC.ERR_ARGS, "wrong hwaddr value"

        if action not in ("accept", "drop",):
            return RPC.ERR_ARGS, "wrong action value"

        if hwaddr in self.__helper.sec_net_configs:
            return RPC.ERR_SYS, "source rule %s exists" % hwaddr

        if action == "accept":
            n_act = router.IXC_SEC_NET_ACT_ACCEPT
        else:
            n_act = router.IXC_SEC_NET_ACT_DROP

        self.__helper.sec_net_configs[hwaddr] = {"global_action": action, "rules": []}

        byte_hwaddr = netutils.str_hwaddr_to_bytes(hwaddr)
        return 0, self.__helper.router.sec_net_add_src(byte_hwaddr, n_act)

    def sec_net_del_src(self, hwaddr: str):
        if not netutils.is_hwaddr(hwaddr):
            return RPC.ERR_ARGS, "wrong hwaddr value"

        if hwaddr not in self.__helper.sec_net_configs: return

        del self.__helper.sec_net_configs[hwaddr]

        byte_hwaddr = netutils.str_hwaddr_to_bytes(hwaddr)

        return 0, self.__helper.router.sec_net_del_src(byte_hwaddr)

    def sec_net_add_dst(self, hwaddr: str, subnet: str, prefix: int, is_ipv6=False):
        if not netutils.is_hwaddr(hwaddr):
            return RPC.ERR_ARGS, "wrong hwaddr value"
        byte_hwaddr = netutils.str_hwaddr_to_bytes(hwaddr)

        if prefix < 0:
            return RPC.ERR_ARGS, "wrong prefix value %s" % prefix

        if is_ipv6 and prefix > 128:
            return RPC.ERR_ARGS, "wrong prefix value %s" % prefix

        if not is_ipv6 and prefix > 32:
            return RPC.ERR_ARGS, "wrong prefix value %s" % prefix

        if is_ipv6:
            fa = socket.AF_INET6
        else:
            fa = socket.AF_INET

        byte_subnet = socket.inet_pton(fa, subnet)

        if hwaddr not in self.__helper.sec_net_configs:
            return RPC.ERR_SYS, "not found source rule %s" % hwaddr

        # 首先检查规则是否存在
        rules = self.__helper.sec_net_configs[hwaddr]["rules"]
        # 如果存在
        for _subnet, _prefix in rules:
            if _subnet == subnet and prefix == _prefix: return 0, True

        rules.append((subnet, prefix,))

        return 0, self.__helper.router.sec_net_add_dst(byte_hwaddr, byte_subnet, prefix, is_ipv6)

    def sec_net_config_get(self):
        return 0, self.__helper.sec_net_configs

    def net_monitor_set(self, hwaddr: str, enable=False):
        if enable and not netutils.is_hwaddr(hwaddr):
            return RPC.ERR_ARGS, "wrong hwaddr value"

        self.__helper.net_monitor_configs["hwaddr"] = hwaddr

        if not enable:
            self.__helper.net_monitor_configs["enable"] = False
            return 0, self.__helper.router.net_monitor_set(False, b"")

        byte_hwaddr = netutils.str_hwaddr_to_bytes(hwaddr)
        self.__helper.net_monitor_configs["enable"] = True

        return 0, self.__helper.router.net_monitor_set(True, byte_hwaddr)

    def net_monitor_config_get(self):
        return 0, self.__helper.net_monitor_configs

    def qos_set_tunnel_first(self, address: str, is_ipv6: bool):
        if is_ipv6 and not netutils.is_ipv6_address(address):
            return RPC.ERR_ARGS, "wrong IPv6 address argument"
        if not is_ipv6 and not netutils.is_ipv4_address(address):
            return RPC.ERR_ARGS, "wrong IPv4 address argument"

        return 0, self.__helper.router.qos_set_tunnel_first(address, is_ipv6)

    def qos_unset_tunnel(self):
        return 0, None

    def qos_set_mpkt_first_size(self, size: int):
        if size != 0:
            if size < 64 or size > 512:
                return 0, False
            ''''''
        self.__helper.wan_configs["qos"]["mpkt_first_size"] = size

        rs = self.__helper.router.qos_set_mpkt_first_size(size)

        self.__helper.save_wan_configs()

        return 0, rs

    def qos_add_first_host_hwaddr(self, hwaddr: str, comment=""):
        dic = self.__helper.router_configs['qos_first_host']

        if hwaddr in dic:
            return 0, False

        byte_hwaddr = netutils.str_hwaddr_to_bytes(hwaddr)
        rs = self.__helper.router.qos_add_first_host_hwaddr(byte_hwaddr)

        dic[hwaddr] = comment
        self.__helper.save_router_configs()

        return 0, rs

    def qos_del_first_host_hwaddr(self, hwaddr: str):
        dic = self.__helper.router_configs['qos_first_host']

        if hwaddr not in dic:
            return 0, None

        byte_hwaddr = netutils.str_hwaddr_to_bytes(hwaddr)
        rs = self.__helper.router.qos_del_first_host_hwaddr(byte_hwaddr)

        del dic[hwaddr]
        self.__helper.save_router_configs()

        return 0, rs

    def passthrough_device_add(self, hwaddr: str, is_passdev=False, comment=""):
        if not netutils.is_hwaddr(hwaddr):
            return RPC.ERR_ARGS, "wrong hwaddr value"

        byte_hwaddr = netutils.str_hwaddr_to_bytes(hwaddr)

        b = self.__helper.router.passthrough_device_add(byte_hwaddr, is_passdev)
        dic = self.__helper.router_configs['passthrough']

        # 这里的0和1表示是否是直通到passdev设备
        if not is_passdev:
            dic[hwaddr] = "0|%s" % comment
        else:
            dic[hwaddr] = "1|%s" % comment

        self.__helper.save_router_configs()

        return 0, b

    def passthrough_device_del(self, hwaddr: str):
        if not netutils.is_hwaddr(hwaddr):
            return RPC.ERR_ARGS, "wrong hwaddr value"

        byte_hwaddr = netutils.str_hwaddr_to_bytes(hwaddr)
        self.__helper.router.passthrough_device_del(byte_hwaddr)
        dic = self.__helper.router_configs['passthrough']

        if hwaddr in dic:
            del dic[hwaddr]
            self.__helper.save_router_configs()

        return 0, None

    def passthrough_set_vid_for_passdev(self, vid: int):
        if vid < 0 or vid > 4094: return 0, False

        dic = self.__helper.router_configs['config']
        dic['vlanid_for_passdev'] = vid
        self.__helper.save_router_configs()

        return 0, self.__helper.router.passthrough_set_vid_for_passdev(vid)

    def cpu_num(self):
        return 0, self.__helper.router.cpu_num()

    def bind_cpu(self, cpu_no: int):
        b = self.__helper.router.bind_cpu(cpu_no)
        if b:
            self.__helper.router_configs["config"]["bind_cpu"] = cpu_no

        self.__helper.save_router_configs()

        return 0, b

    def router_start_time(self):
        return 0, self.__helper.router.router_start_time()

    def traffic_log_enable(self, enable):
        return 0, self.__helper.router.traffic_log_enable(enable)

    def icmpv6_dns_set(self, dnsserver: bytes):
        return 0, self.__helper.router.icmpv6_dns_set(dnsserver)

    def icmpv6_dns_unset(self):
        return 0, self.__helper.router.icmpv6_dns_unset()

    def icmpv6_wan_dnsserver_get(self):
        return 0, self.__helper.router.icmpv6_wan_dnsserver_get()


class helper(object):
    __WAN_BR_NAME = None
    __LAN_BR_NAME = None
    __PASS_BR_NAME = None

    __LAN_NAME = None
    __WAN_NAME = None
    __PASS_NAME = None

    __router = None
    __debug = None

    __if_lan_fd = None
    __if_wan_fd = None
    __if_pass_fd = None

    __lan_configs = None
    __wan_configs = None
    __router_configs = None
    __port_map_configs = None
    __net_monitor_configs = None
    __sec_net_rules = None

    __is_linux = None
    __scgi_fd = None

    __pppoe = None
    __pppoe_enable = None
    __pppoe_user = None
    __pppoe_passwd = None
    __pppoe_heartbeat = None

    __conf_dir = None
    __rpc_instance = None

    def load_lan_configs(self):
        path = "%s/lan.ini" % self.__conf_dir
        self.__lan_configs = conf.ini_parse_from_file(path)
        if "passthrough" not in self.__lan_configs:
            self.__lan_configs["passthrough"] = {}
        o = self.__lan_configs["passthrough"]
        if "if_name" not in o: o["if_name"] = ""
        if "enable" not in o: o["enable"] = "0"

    def save_lan_configs(self):
        path = "%s/lan.ini" % self.__conf_dir
        conf.save_to_ini(self.__lan_configs, path)

    def load_wan_configs(self):
        path = "%s/wan.ini" % self.__conf_dir
        self.__wan_configs = conf.ini_parse_from_file(path)
        if "qos" not in self.__wan_configs:
            self.__wan_configs["qos"] = {
                "mpkt_first_size": "0"
            }
        return

    def save_wan_configs(self):
        path = "%s/wan.ini" % self.__conf_dir
        conf.save_to_ini(self.__wan_configs, path)

    def load_router_configs(self):
        path = "%s/router.ini" % self.__conf_dir
        self.__router_configs = conf.ini_parse_from_file(path)
        if "config" not in self.__router_configs:
            self.__router_configs["config"] = {}
        dic = self.__router_configs["config"]

        if "bind_cpu" not in dic:
            dic["bind_cpu"] = -1

        if "ip_tcp_mss" not in dic:
            dic["ip_tcp_mss"] = 0
        if "ip6_tcp_mss" not in dic:
            dic["ip6_tcp_mss"] = 0
        if "vlanid_for_passdev" not in dic:
            dic["vlanid_for_passdev"] = 0

        if "passthrough" not in self.__router_configs:
            self.__router_configs["passthrough"] = {}

        if "qos_first_host" not in self.__router_configs:
            self.__router_configs["qos_first_host"] = {}

    def load_port_map_configs(self):
        path = "%s/port_map.ini" % self.__conf_dir
        self.__port_map_configs = conf.ini_parse_from_file(path)

    def load_net_monitor_configs(self):
        path = "%s/net_monitor.json" % self.__conf_dir
        with open(path, "r") as f:
            s = f.read()
        f.close()
        self.__net_monitor_configs = json.loads(s)

    def load_sec_net_configs(self):
        path = "%s/sec_net.json" % self.__conf_dir
        with open(path, "r") as f:
            s = f.read()
        f.close()
        self.__sec_net_rules = json.loads(s)

    def save_sec_net_configs(self):
        path = "%s/sec_net.json" % self.__conf_dir
        with open(path, "w") as f:
            f.write(json.dumps(self.__sec_net_rules))
        f.close()

    def save_net_monitor_configs(self):
        path = "%s/net_monitor.json" % self.__conf_dir
        with open(path, "w") as f:
            f.write(json.dumps(self.__net_monitor_configs))
        f.close()

    def save_router_configs(self):
        path = "%s/router.ini" % self.__conf_dir
        conf.save_to_ini(self.__router_configs, path)

    def save_port_map_configs(self):
        path = "%s/port_map.ini" % self.__conf_dir
        conf.save_to_ini(self.__port_map_configs, path)

    def reset_port_map(self):
        for name in self.__port_map_configs:
            o = self.__port_map_configs[name]
            protocol = int(o["protocol"])
            port = int(o["port"])
            self.router.port_map_del(protocol, port)
        self.load_port_map_configs()
        for name in self.__port_map_configs:
            o = self.__port_map_configs[name]
            protocol = int(o["protocol"])
            port = int(o["port"])
            address = o["address"]
            self.router.port_map_add(protocol, port, address)

    @property
    def router(self):
        return self.__router

    @property
    def is_linux(self):
        return self.__is_linux

    @property
    def lan_configs(self):
        return self.__lan_configs

    @property
    def wan_configs(self):
        return self.__wan_configs

    @property
    def router_configs(self):
        return self.__router_configs

    @property
    def port_map_configs(self):
        return self.__port_map_configs

    @property
    def debug(self):
        return self.__debug

    @property
    def pppoe_user(self):
        return self.__pppoe_user

    @property
    def pppoe_passwd(self):
        return self.__pppoe_passwd

    @property
    def net_monitor_configs(self):
        return self.__net_monitor_configs

    @property
    def sec_net_configs(self):
        return self.__sec_net_rules

    def release(self):
        if self.__pppoe_enable:
            self.router.pppoe_reset()
            # 等待一段时间,以便系统能够结束相关清理工作
            time.sleep(10)
        if self.is_linux:
            os.system("ip link set %s down" % self.__LAN_NAME)
            os.system("ip link set %s down" % self.__WAN_NAME)
            os.system("ip link set %s down" % self.__LAN_BR_NAME)
            os.system("ip link set %s down" % self.__WAN_BR_NAME)
            os.system("ip link del %s" % self.__LAN_BR_NAME)
            os.system("ip link del %s" % self.__WAN_BR_NAME)
        else:
            os.system("ifconfig %s destroy" % self.__LAN_BR_NAME)
            os.system("ifconfig %s destroy" % self.__WAN_BR_NAME)

        self.stop_pass()

        if self.__if_lan_fd > 0:
            self.router.netif_delete(router.IXC_NETIF_LAN)
        if self.__if_wan_fd > 0:
            self.router.netif_delete(router.IXC_NETIF_WAN)

        self.__if_lan_fd = -1
        self.__if_wan_fd = -1

    def linux_br_create(self, br_name: str, added_bind_ifs: list):
        cmds = [
            "ip link add name %s type bridge" % br_name,
            "ip link set dev %s up" % br_name,
            # "echo 1 >/proc/sys/net/ipv6/conf/all/forwarding",
            # "echo 1 > /proc/sys/net/ipv4/ip_forward"
        ]

        for cmd in cmds: os.system(cmd)
        for if_name in added_bind_ifs:
            cmd = "ip link set dev %s master %s" % (if_name, br_name,)
            os.system(cmd)
        self.config_multicast_snooping()

    def freebsd_br_create(self, added_bind_ifs: list):
        fd = os.popen("ifconfig bridge create")
        s = fd.read()
        fd.close()
        s = s.replace("\n", "")
        s = s.replace(" ", "")

        _list = ["ifconfig %s" % s, ]
        for name in added_bind_ifs:
            _list.append("addm %s" % name)
        _list.append("up")
        cmd = " ".join(_list)
        os.system(cmd)

        return s

    def config_multicast_snooping(self):
        """桥接网络不支持igmp multicast snooping,导致IPv6可能在工作一段时间后异常,需要关闭
        """
        cur_pwd = os.getcwd()
        os.chdir("/sys/devices/virtual/net")
        _listdir = os.listdir()
        br_devices = []
        for name in _listdir:
            p = name.find("br")
            if p < 0: continue
            br_devices.append(name)

        for br_device in br_devices:
            cmd = "echo 0 > %s/bridge/multicast_snooping" % br_device
            os.system(cmd)
        os.chdir(cur_pwd)

    def start_security(self):
        """打开安全网络
        """
        self.load_net_monitor_configs()
        self.load_sec_net_configs()

        hwaddr = self.__net_monitor_configs["hwaddr"]
        if self.__net_monitor_configs["enable"]:
            byte_hwaddr = netutils.str_hwaddr_to_bytes(hwaddr)

            self.router.net_monitor_set(True, byte_hwaddr)

        for hwaddr in self.__sec_net_rules:
            byte_hwaddr = netutils.str_hwaddr_to_bytes(hwaddr)
            o = self.__sec_net_rules[hwaddr]

            action = o["global_action"]
            rules = o["rules"]

            if action == "accept":
                n_action = router.IXC_SEC_NET_ACT_ACCEPT
            else:
                n_action = router.IXC_SEC_NET_ACT_DROP

            x = self.router.sec_net_add_src(byte_hwaddr, n_action)
            if not x: continue

            for rule in rules:
                t = tuple(rule)
                ipaddr, prefix = t
                is_ipv6 = False
                if netutils.is_ipv4_address(ipaddr):
                    byte_ipaddr = socket.inet_pton(socket.AF_INET, ipaddr)
                else:
                    is_ipv6 = True
                    byte_ipaddr = socket.inet_pton(socket.AF_INET6, ipaddr)
                prefix = int(prefix)
                self.router.sec_net_add_dst(byte_hwaddr, byte_ipaddr, prefix, is_ipv6)
            ''''''

    def start_lan(self):
        self.load_lan_configs()
        lan_ifconfig = self.__lan_configs["if_config"]
        lan_phy_ifname = lan_ifconfig["phy_ifname"]
        hwaddr = lan_ifconfig["hwaddr"]

        self.__if_lan_fd, self.__LAN_NAME = self.__router.netif_create(self.__LAN_NAME, router.IXC_NETIF_LAN)

        self.router.netif_set_hwaddr(router.IXC_NETIF_LAN, netutils.str_hwaddr_to_bytes(hwaddr))

        if self.is_linux:
            _list = lan_phy_ifname.split(",")
            lan_ifs = []
            for devname in _list:
                devname = devname.strip()
                lan_ifs.append(devname)

            self.linux_br_create(self.__LAN_BR_NAME, lan_ifs + [self.__LAN_NAME])

            for devname in lan_ifs:
                os.system("ip link set %s promisc on" % devname)
                # os.system("ip link set %s promisc on" % self.__LAN_NAME)
                os.system("ip link set %s up" % devname)
            # 设置内网桥接网卡MTU为1400,目的为了本机能够被正常访问
            # os.system("ip link set dev %s mtu 1400" % self.__LAN_BR_NAME)
        else:
            self.__LAN_BR_NAME = self.freebsd_br_create([lan_phy_ifname, self.__LAN_NAME, ])

            os.system("ifconfig %s promisc" % lan_phy_ifname)
            # os.system("ifconfig %s promisc" % self.__WAN_NAME)
            os.system("ifconfig %s up" % lan_phy_ifname)

        lan_addr = lan_ifconfig["ip_addr"]
        manage_addr = lan_ifconfig["manage_addr"]
        mask = lan_ifconfig["mask"]

        byte_ipaddr = socket.inet_pton(socket.AF_INET, lan_addr)
        prefix = netutils.mask_to_prefix(mask, False)

        self.router.netif_set_ip(router.IXC_NETIF_LAN, byte_ipaddr, prefix, False)

        if self.is_linux:
            os.system("ip -4 addr add %s/%s dev %s" % (manage_addr, prefix, self.__LAN_BR_NAME))
            os.system("ip -4 route add default via %s" % lan_addr)
            # os.system("echo 1 > /proc/sys/net/ipv4/ip_forward")

        # IPv6
        enable_static_ipv6 = bool(int(lan_ifconfig["enable_static_ipv6"]))
        enable_ipv6_pass = bool(int(lan_ifconfig["enable_ipv6_pass"]))
        enable_ipv6_security = bool(int(lan_ifconfig["enable_ipv6_security"]))
        ip6_addr, v6_prefix = netutils.parse_ip_with_prefix(lan_ifconfig["ip6_addr"])

        byte_ip6addr = socket.inet_pton(socket.AF_INET6, ip6_addr)

        if enable_static_ipv6:
            self.router.netif_set_ip(router.IXC_NETIF_LAN, byte_ip6addr, int(v6_prefix),
                                     True)
        self.router.route_ipv6_pass_enable(enable_ipv6_pass)
        self.router.ip6sec_enable(enable_ipv6_security)
        self.router.g_manage_addr_set(manage_addr, False)

    def passdev_set(self, config: dict):
        configs = self.lan_configs["passthrough"]
        configs["if_name"] = config["if_name"]
        configs["enable"] = config["enable"]

        self.stop_pass()
        self.start_pass()

    def start_pass(self):
        configs = self.lan_configs["passthrough"]
        enable = bool(int(configs["enable"]))
        if not enable: return
        if self.__if_pass_fd >= 0: return

        ifname = configs["if_name"]
        if ifname not in osnet.get_if_net_devices(): return

        self.__if_pass_fd, self.__PASS_NAME = self.__router.netif_create("ixcpass", router.IXC_NETIF_PASS)
        if self.is_linux:
            self.linux_br_create(self.__PASS_BR_NAME, [ifname, self.__PASS_NAME, ])
            os.system("ip link set %s promisc on" % ifname)
            os.system("ip link set %s promisc on" % self.__PASS_NAME)
            os.system("ip link set %s up" % ifname)
            # 关闭外网IPv6支持
            os.system("echo 1 > /proc/sys/net/ipv6/conf/%s/disable_ipv6" % self.__PASS_BR_NAME)
            os.system("echo 1 > /proc/sys/net/ipv6/conf/%s/disable_ipv6" % ifname)
        else:
            pass

    def stop_pass(self):
        if self.__if_pass_fd < 0: return
        if self.is_linux:
            os.system("ip link set %s down" % self.__PASS_NAME)
            os.system("ip link set %s down" % self.__PASS_BR_NAME)
            os.system("ip link set %s nomaster" % self.__PASS_NAME)
            os.system("ip link del %s" % self.__PASS_BR_NAME)
        else:
            os.system("ifconfig %s destroy" % self.__PASS_BR_NAME)
        self.__router.netif_delete(router.IXC_NETIF_PASS)
        self.__if_pass_fd = -1

    def start_wan(self):
        self.load_wan_configs()

        wan_public = self.__wan_configs["public"]
        wan_phy_ifname = wan_public["phy_ifname"]
        wan_ifhwaddr = wan_public["hwaddr"]
        ipv4 = self.__wan_configs["ipv4"]

        self.__pppoe = pppoe.pppoe(self)
        self.__if_wan_fd, self.__WAN_NAME = self.__router.netif_create(self.__WAN_NAME, router.IXC_NETIF_WAN)
        self.router.netif_set_hwaddr(router.IXC_NETIF_WAN, netutils.str_hwaddr_to_bytes(wan_ifhwaddr))

        if self.is_linux:
            self.linux_br_create(self.__WAN_BR_NAME, [wan_phy_ifname, self.__WAN_NAME, ])
            os.system("ip link set %s promisc on" % wan_phy_ifname)
            os.system("ip link set %s promisc on" % self.__WAN_NAME)
            os.system("ip link set %s up" % wan_phy_ifname)
            # 关闭外网IPv6支持
            os.system("echo 1 > /proc/sys/net/ipv6/conf/%s/disable_ipv6" % self.__WAN_BR_NAME)
            os.system("echo 1 > /proc/sys/net/ipv6/conf/%s/disable_ipv6" % wan_phy_ifname)
        else:
            pass

        wan_pppoe = self.__wan_configs["pppoe"]
        wan_public = self.__wan_configs["public"]
        internet_type = wan_public["internet_type"]
        ip4_mtu = int(wan_public.get("ip4_mtu", 1500))
        ip6_mtu = int(wan_public.get("ip6_mtu", 1280))

        if internet_type == "pppoe":
            self.__pppoe_enable = True
        else:
            self.__pppoe_enable = False

        if self.__pppoe_enable:
            # PPPoE需要减去头部的8个字节
            ip4_mtu -= 8
            # 由于IPv6最小mtu为1280,只有大于1288时才减去8
            if ip6_mtu >= 1288: ip6_mtu -= 8
            self.__pppoe_user = wan_pppoe["user"]
            self.__pppoe_passwd = wan_pppoe["passwd"]
            self.__pppoe_heartbeat = bool(int(wan_pppoe["heartbeat"]))

            self.router.pppoe_enable(True)
            self.router.pppoe_start()

            self.router.netif_set_mtu(router.IXC_NETIF_WAN, ip4_mtu, False)
            self.router.netif_set_mtu(router.IXC_NETIF_WAN, ip6_mtu, True)

            return

        # 设置好WAN网口的MTU值
        self.router.netif_set_mtu(router.IXC_NETIF_WAN, ip4_mtu, False)
        self.router.netif_set_mtu(router.IXC_NETIF_WAN, ip6_mtu, True)

        # MTU设置必须在此之前,否则DHCP上网无法正确设置MTU
        if internet_type.lower() != "static-ip": return

        ip_addr = ipv4["address"]
        mask = ipv4["mask"]
        default_gw = ipv4.get("default_gw", None)

        byte_ipaddr = socket.inet_pton(socket.AF_INET, ip_addr)
        prefix = netutils.mask_to_prefix(mask, 0)

        self.router.netif_set_ip(router.IXC_NETIF_WAN, byte_ipaddr, prefix, False)
        if not default_gw: return

        byte_gw = socket.inet_pton(socket.AF_INET, default_gw)
        byte_subnet = socket.inet_pton(socket.AF_INET, "0.0.0.0")

        self.router.route_add(byte_subnet, 0, byte_gw, False)

        qos = self.wan_configs["qos"]
        try:
            mpkt_first_size = int(qos['mpkt_first_size'])
        except ValueError:
            mpkt_first_size = 0

        self.router.qos_set_mpkt_first_size(mpkt_first_size)

    def set_gw_ipaddr(self, ipaddr: str, prefix: int, is_ipv6=False):
        if is_ipv6:
            fa = socket.AF_INET6
        else:
            fa = socket.AF_INET
        byte_ip = socket.inet_pton(fa, ipaddr)

        self.router.netif_set_ip(router.IXC_NETIF_LAN, byte_ip, prefix, False)

    def set_wan_mtu(self, mtu: int, is_ipv6=False):
        self.router.netif_set_mtu(router.IXC_NETIF_WAN, mtu, is_ipv6)

    def get_manage_addr(self):
        return self.lan_configs["if_config"]["manage_addr"]

    def set_router(self):
        """
        :return:
        """
        self.load_router_configs()

        conf = self.__router_configs["config"]
        try:
            cpu_no = int(conf["bind_cpu"])
        except ValueError:
            cpu_no = -1
            conf["bind_cpu"] = -1
            self.save_router_configs()

        if cpu_no < 0: return
        if self.router.cpu_num() <= cpu_no:
            conf["bind_cpu"] = -1
            self.save_router_configs()
            return
        self.router.bind_cpu(cpu_no)

        # 设置TCP MSS
        try:
            ip4_tcp_mss = int(conf['ip_tcp_mss'])
        except ValueError:
            ip4_tcp_mss = 0
        if ip4_tcp_mss < 0: ip4_tcp_mss = 0

        try:
            ip6_tcp_mss = int(conf['ip6_tcp_mss'])
        except ValueError:
            ip6_tcp_mss = 0
        if ip6_tcp_mss < 0: ip6_tcp_mss = 0

        self.__router.route_tcp_mss_set(ip4_tcp_mss, False)
        self.__router.route_tcp_mss_set(ip6_tcp_mss, True)

        passthrough = self.__router_configs["passthrough"]
        for hwaddr, enable_with_comment in passthrough.items():
            p = enable_with_comment.find("|")
            if p != 1:
                is_passdev = False
            else:
                try:
                    is_passdev = bool(int(enable_with_comment[0:p]))
                except ValueError:
                    is_passdev = False
                ''''''
            ''''''
            byte_hwaddr = netutils.str_hwaddr_to_bytes(hwaddr)
            self.router.passthrough_device_add(byte_hwaddr, is_passdev)
        self.router.passthrough_set_vid_for_passdev(int(conf["vlanid_for_passdev"]))

    def port_map_add(self, protocol: int, port: int, address: str, alias_name: str):
        self.__port_map_configs[alias_name] = {
            "protocol": protocol,
            "port": port,
            "address": address
        }
        self.save_port_map_configs()
        self.reset_port_map()

    def port_map_del(self, protocol: int, port: int):
        alias_name = None
        for name in self.__port_map_configs:
            o = self.__port_map_configs[name]
            p = int(o["protocol"])
            _port = int(o["port"])
            if p == protocol and _port == port:
                alias_name = name
                break
            ''''''
        if alias_name: del self.__port_map_configs[alias_name]
        self.save_port_map_configs()
        self.reset_port_map()

    def __init__(self, debug: bool):
        self.__conf_dir = "%s/../../ixc_configs/router" % os.path.dirname(__file__)
        self.__debug = debug
        self.__router = router.router()
        self.__if_lan_fd = -1
        self.__if_wan_fd = -1
        self.__if_pass_fd = -1

        self.__WAN_BR_NAME = "ixcwanbr"
        self.__LAN_BR_NAME = "ixclanbr"
        self.__PASS_BR_NAME = "ixcpassbr"

        self.__LAN_NAME = "ixclan"
        self.__WAN_NAME = "ixcwan"
        self.__PASS_NAME = "ixcpass"

        self.__wan_configs = {}
        self.__is_linux = sys.platform.startswith("linux")
        self.__rpc_instance = rpc(self)

        if not debug: self.__router.clog_set("/tmp/ixcsys/router/stdout.log", "/tmp/ixcsys/router/stderr.log")

        # FreeBSD if_tap.ko
        if not self.is_linux:
            fd = os.popen("kldstat")
            s = fd.read()
            fd.close()
            p = s.find("if_tap.ko")
            if p < 0: os.system("kldload if_tap")

    def start(self):
        self.start_lan()
        self.start_wan()

        self.set_router()

        self.load_port_map_configs()
        self.reset_port_map()

        self.start_security()
        self.start_pass()

    @property
    def pppoe_dnsservers(self):
        return self.__pppoe.ipcp.get_dnsservers()

    @property
    def router(self):
        return self.__router

    def pppoe_session_handle(self, protocol: int, byte_data: bytes):
        """
        """
        self.__pppoe.handle_packet_from_ns(protocol, byte_data)

    @property
    def pppoe_user(self):
        return self.__pppoe_user

    @property
    def pppoe_passwd(self):
        return self.__pppoe_passwd

    @property
    def pppoe_heartbeat(self):
        return self.__pppoe_heartbeat

    def pppoe_force_re_dial(self):
        """强制重新连接
        """
        # 未开启PPPoE那么不执行
        if not self.__pppoe_enable: return

        logging.print_alert("start PPPoE re-dial")
        self.__pppoe.reset()

    def rpc_fn_call(self, name: str, arg_data: bytes):
        """
        :return (is_error,byte_message)
        """
        dic = pickle.loads(arg_data)
        if not isinstance(dic, dict):
            return RPC.ERR_SYS, "wrong RPC request procotol"

        if "args" not in dic:
            return RPC.ERR_SYS, "wrong RPC request procotol"

        if "kwargs" not in dic:
            return RPC.ERR_SYS, "wrong RPC request procotol"

        args = dic["args"]
        kwargs = dic["kwargs"]

        if not isinstance(args, tuple) or (not isinstance(kwargs, dict)):
            return RPC.ERR_SYS, "wrong RPC request procotol"

        return self.__rpc_instance.call(name, *args, **kwargs)

    def tell(self, s: str, *args):
        """
        """
        p = s.find(" ")
        v = ""
        if p <= 0:
            cmd = s
        else:
            cmd = s[0:p]
            p += 1
            v = s[p:]
        if cmd == "lcp_start":
            if self.__pppoe: self.__pppoe.start_lcp()
            return
        if cmd == "lcp_stop":
            if self.__pppoe: self.__pppoe.stop_lcp()
            return
        if cmd == "pppoe_ac_name":
            ac_name = v
            self.__pppoe.record_ac_name(ac_name)
            return
        if cmd == "pppoe_selected_ac_name":
            ac_name = v
            self.__pppoe.tell_selected_ac_name(ac_name)
            return
        logging.print_error("not found system command %s" % cmd)

    def calc_md5(self, byte_data: bytes):
        """计算MD5
        """
        md5 = hashlib.md5()
        md5.update(byte_data)

        return md5.digest()

    def loop(self):
        """
        """
        self.__pppoe.loop()
