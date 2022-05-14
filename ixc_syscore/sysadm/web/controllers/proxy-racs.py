#!/usr/bin/env python3

import pywind.lib.netutils as netutils

import ixc_syscore.sysadm.web.controllers.controller as base_controller

import ixc_syslib.pylib.RPCClient as RPC


class controller(base_controller.BaseController):
    def myinit(self):
        self.request.set_allow_methods(["POST"])
        return True

    def handle_post(self):
        self.finish_with_json({})

    def handle(self):
        kv_map = {
            "connection": {
                "enable": 0,
                "enable_ip6": 0,
                "host": "www.example.com",
                "port": 1999,
            },
            "security": {
                "shared_key": "ixcsys",
                "private_key": "ixcsys"
            },
            "network": {
                "enable_ip6": 0,
                "ip_route": "",
                "ip6_route": "",
            }
        }

        for x in kv_map:
            o = kv_map[x]
            for y in o:
                name = "%s.%s" % (x, y)
                value = self.request.get_argument(name, is_seq=False, is_qs=False)
                o[y] = value
            ''''''

        if kv_map["connection"]["enable"]:
            kv_map["connection"]["enable"] = True
        else:
            kv_map["connection"]["enable"] = False

        if kv_map["connection"]["enable_ip6"]:
            kv_map["connection"]["enable_ip6"] = True
        else:
            kv_map["connection"]["enable_ip6"] = False

        try:
            port = int(kv_map["connection"]["port"])
        except ValueError:
            self.json_resp(True, "错误的connection.port值")
            return
        except TypeError:
            self.json_resp(True, "错误的connection.port值")
            return

        if port < 1 or port > 0xfffe:
            self.json_resp(True, "错误的connection.port值范围")
            return

        if not kv_map["security"]["shared_key"] or not kv_map["security"]["private_key"]:
            self.json_resp(True, "共享密钥、私有密钥不能为空")
            return

        if kv_map["network"]["enable_ip6"]:
            kv_map["network"]["enable_ip6"] = True
        else:
            kv_map["network"]["enable_ip6"] = False

        ip_route = kv_map["network"]["ip_route"]
        ip6_route = kv_map["network"]["ip6_route"]

        if not ip_route or not ip6_route:
            self.json_resp(True, "空的IP路由地址或IPv6地址")
            return

        tmp = netutils.parse_ip_with_prefix(ip_route)
        if not tmp:
            self.json_resp(True, "错误的IP路由地址格式")
            return

        ip, prefix = tmp
        if not netutils.is_ipv4_address(ip):
            self.json_resp(True, "错误的IP路由地址格式")
            return
        if prefix > 32 or prefix < 1:
            self.json_resp(True, "错误的IP路由地址格式")
            return

        tmp = netutils.parse_ip_with_prefix(ip6_route)
        if not tmp:
            self.json_resp(True, "错误的IPv6路由地址格式")
            return
        ip6, prefix = tmp
        if not netutils.is_ipv6_address(ip6):
            self.json_resp(True, "错误的IPv6路由地址格式")
            return
        if prefix > 128 or prefix < 1:
            self.json_resp(True, "错误的IPv6路由地址格式")
            return

        RPC.fn_call("proxy", "/config", "racs_cfg_update", kv_map)

        self.json_resp(False, {})

