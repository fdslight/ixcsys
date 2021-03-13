#!/usr/bin/env python3

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

        RPC.fn_call("proxy", "/config", fn, text)

        self.json_resp(False, {})

    def handle_conn(self):
        kv_map = {
            "connection": {
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
                "tunnel_over_https": None
            },
            "tunnel_over_https": {
                "url": "/",
                "auth_id": "ixcsys",
                "enable_https_sni": None,
                "https_sni_host": "www.example.com",
                "strict_https": None
            }
        }

        for x in kv_map:
            o = kv_map[x]
            for y in o:
                name = "%s.%s" % (x, y)
                value = self.request.get_argument(name, is_seq=False, is_qs=False)
                o[y] = value
            ''''''

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
