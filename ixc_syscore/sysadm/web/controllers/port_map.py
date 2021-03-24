#!/usr/bin/env python3

import pywind.lib.netutils as netutils

import ixc_syscore.sysadm.web.controllers.controller as base_controller
import ixc_syslib.pylib.RPCClient as RPC


class controller(base_controller.BaseController):
    def myinit(self):
        self.request.set_allow_methods(["POST"])
        return True

    def handle_add(self):
        name = self.request.get_argument("alias-name", is_seq=False, is_qs=False)
        port = self.request.get_argument("port", is_seq=False, is_qs=False)
        ip = self.request.get_argument("ip", is_seq=False, is_qs=False)
        protocol = self.request.get_argument("protocol", is_seq=False, is_qs=False)

        if not name:
            self.finish_with_json({"is_error": True, "message": "别名不能为空"})
            return

        if not port:
            self.finish_with_json({"is_error": True, "message": "端口不能为空"})
            return

        if not protocol:
            self.finish_with_json({"is_error": True, "message": "协议不能为空"})
            return

        if not ip:
            self.finish_with_json({"is_error": True, "message": "IP地址不能为空"})
            return

        if not netutils.is_port_number(port):
            self.finish_with_json({"is_error": True, "messsage": "错误的端口值"})
            return

        if protocol not in ("TCP", "UDP", "UDPLite",):
            self.finish_with_json({"is_error": True, "messsage": "不支持的协议"})
            return

        if not netutils.is_ipv4_address(ip):
            self.finish_with_json({"is_error": True, "messsage": "错误的IP地址格式"})
            return

        # 此处检查该映射是否存在
        port_map = RPC.fn_call("router", "/config", "port_map_configs_get")

        if protocol == "TCP":
            proto_number = 6
        elif protocol == "UDP":
            proto_number = 17
        else:
            proto_number = 136

        if name in port_map:
            self.finish_with_json({"is_error": True, "messsage": "该别名已经存在,请重新更换"})
            return

        port = int(port)

        for name in port_map:
            o = port_map[name]
            p = int(o["protocol"])
            _port = int(o["port"])
            if p == proto_number and port == _port:
                self.finish_with_json({"is_error": True, "messsage": "映射已经存在,请删除后重试"})
                return
            ''''''
        RPC.fn_call("router", "/config", "port_map_add", proto_number, port, ip, name)
        self.finish_with_json({"is_error": False, "message": "添加成功"})

    def handle_delete(self):
        port = self.request.get_argument("port", is_seq=False, is_qs=False)
        protocol = self.request.get_argument("protocol", is_seq=False, is_qs=False)

        if not port or not protocol:
            self.finish_with_json({"is_error": True, "message": "错误的请求参数"})
            return

        if not netutils.is_port_number(port):
            self.finish_with_json({"is_error": True, "messsage": "错误的端口值"})
            return

        if protocol not in ("TCP", "UDP", "UDPLite",):
            self.finish_with_json({"is_error": True, "messsage": "不支持的协议"})
            return

        if protocol == "TCP":
            proto_number = 6
        elif protocol == "UDP":
            proto_number = 17
        else:
            proto_number = 136
        port = int(port)

        RPC.fn_call("router", "/config", "port_map_del", proto_number, port)

        self.finish_with_json({"is_error": False, "message": "删除成功"})

    def handle(self):
        action = self.request.get_argument("action", is_seq=False, is_qs=False)
        if not action:
            self.handle_add()
        else:
            self.handle_delete()
