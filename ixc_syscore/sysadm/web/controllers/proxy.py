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

    def handle_rules(self, _type: str):
        text = self.request.get_argument("text", is_seq=False, is_qs=False)

        if not text:
            self.json_resp(True, "未提交任何表单数据")
            return

        fn = ""
        if _type == "dns":
            fn = "dns_rule_update"
        elif _type == "proxy-ip":
            fn = "proxy_ip_rule_update"
        else:
            fn = "pass_ip_rule_update"

        is_ok, err_msg = RPC.fn_call("proxy", "/config", fn, text)

        if not is_ok:
            err_msg = "规则错误,发生在 " + err_msg

        is_err = not is_ok

        self.json_resp(is_err, err_msg)

    def handle_conn(self):
        kv_map = {
            "connection": {
                "enable": None,
                "enable_ipv6": None,
                "host": None,
                "port": None,
                "tunnel_type": None,
                "crypto_module": None,
                "conn_timeout": None,
                "username": None,
                "password": None,
                "udp_tunnel_redundancy": None,
                "enable_heartbeat": None,
                "heartbeat_timeout": None,
                "tunnel_over_https": None,
                "self_no_fwd_enable": None,
            },
            "tunnel_over_https": {
                "url": "/",
                "auth_id": "ixcsys",
                "enable_https_sni": None,
                "https_sni_host": "www.example.com",
                "strict_https": None,
                "ciphers": "NULL"
            },
            "src_filter": {
                "enable": None,
                "ip_range": None,
                "ip6_range": None,
                "protocol": None,
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
            kv_map["connection"]["enable"] = "1"
        else:
            kv_map["connection"]["enable"] = "0"

        if kv_map["connection"]["enable_ipv6"]:
            kv_map["connection"]["enable_ipv6"] = "1"
        else:
            kv_map["connection"]["enable_ipv6"] = "0"

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

        try:
            conn_timeout = int(kv_map["connection"]["conn_timeout"])
        except ValueError:
            self.json_resp(True, "错误的连接超时值")
            return
        except TypeError:
            self.json_resp(True, "错误的连接超时值")
            return

        if conn_timeout < 20:
            self.json_resp(True, "连接超时应等于大于20s")
            return

        try:
            heartbeat_timeout = int(kv_map["connection"]["heartbeat_timeout"])
        except ValueError:
            self.json_resp(True, "错误的连接心跳值")
            return
        except TypeError:
            self.json_resp(True, "错误的连接心跳值")
            return

        if heartbeat_timeout < 10:
            self.json_resp(True, "心跳值应大于或者等于10s")
            return

        if kv_map["connection"]["tunnel_type"] not in ("tcp", "udp",):
            self.json_resp(True, "错误的隧道协议类型")
            return

        if not kv_map["connection"]["username"] or not kv_map["connection"]["password"]:
            self.json_resp(True, "空的用户名或者密码")
            return

        if kv_map["connection"]["udp_tunnel_redundancy"]:
            kv_map["connection"]["udp_tunnel_redundancy"] = "1"
        else:
            kv_map["connection"]["udp_tunnel_redundancy"] = "0"

        if kv_map["connection"]["enable_heartbeat"]:
            kv_map["connection"]["enable_heartbeat"] = "1"
        else:
            kv_map["connection"]["enable_heartbeat"] = "0"

        if kv_map["connection"]["tunnel_over_https"]:
            kv_map["connection"]["tunnel_over_https"] = "1"
        else:
            kv_map["connection"]["tunnel_over_https"] = "0"

        if kv_map["tunnel_over_https"]["enable_https_sni"]:
            kv_map["tunnel_over_https"]["enable_https_sni"] = "1"
        else:
            kv_map["tunnel_over_https"]["enable_https_sni"] = "0"

        if kv_map["tunnel_over_https"]["strict_https"]:
            kv_map["tunnel_over_https"]["strict_https"] = "1"
        else:
            kv_map["tunnel_over_https"]["strict_https"] = "0"

        if not kv_map["tunnel_over_https"]["url"]:
            self.json_resp(True, "HTTPS隧道的url不能为空")
            return

        if kv_map["tunnel_over_https"]["url"][0] != "/":
            self.json_resp(True, "HTTPS隧道的url值格式错误")
            return

        if kv_map["tunnel_over_https"]["ciphers"].strip() == ",":
            self.json_resp(True, "错误的TLS加密算法")
            return

        if kv_map["src_filter"]["enable"]:
            kv_map["src_filter"]["enable"] = "1"
        else:
            kv_map["src_filter"]["enable"] = "0"

        if kv_map["src_filter"]["protocol"] not in ("TCP", "UDP", "UDPLite", "ALL",):
            self.json_resp(True, "不支持的源端代理协议")
            return

        ip_range = kv_map["src_filter"]["ip_range"]
        ip6_range = kv_map["src_filter"]["ip6_range"]

        if not ip_range or not ip6_range:
            self.json_resp(True, "空的源端代理IP地址或IPv6地址")
            return

        tmp = netutils.parse_ip_with_prefix(ip_range)
        if not tmp:
            self.json_resp(True, "错误的源端代理IP地址格式")
            return

        ip, prefix = tmp
        if not netutils.is_ipv4_address(ip):
            self.json_resp(True, "错误的源端代理IP地址格式")
            return
        if prefix > 32:
            self.json_resp(True, "错误的源端代理IP地址格式")
            return

        tmp = netutils.parse_ip_with_prefix(ip6_range)
        if not tmp:
            self.json_resp(True, "错误的源端代理IPv6地址格式")
            return
        ip6, prefix = tmp
        if not netutils.is_ipv6_address(ip6):
            self.json_resp(True, "错误的源端代理IPv6地址格式")
            return
        if prefix > 128:
            self.json_resp(True, "错误的源端代理IPv6地址格式")
            return

        RPC.fn_call("proxy", "/config", "conn_cfg_update", kv_map)
        self.json_resp(False, {})

    def handle(self):
        _type = self.request.get_argument("type", is_seq=False, is_qs=True)
        _types = (
            "conn", "dns", "proxy-ip", "pass-ip",
        )

        if _type not in _types:
            self.json_resp(True, "错误的请求类型")
            return

        if _type != "conn":
            self.handle_rules(_type)
            return
        self.handle_conn()
