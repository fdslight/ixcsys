#!/usr/bin/env python3

from pywind.global_vars import global_vars
import pywind.lib.netutils as netuitls
import ixc_syscore.sysadm.web.controllers.controller as base_controller


class controller(base_controller.BaseController):
    @property
    def sysadm(self):
        return global_vars["ixcsys.sysadm"]

    def myinit(self):
        self.request.set_allow_methods(["GET"])
        return True

    def add_proxy(self):
        name = self.request.get_argument("name", is_seq=False, is_qs=False)
        host = self.request.get_argument("host", is_seq=False, is_qs=False)
        port = self.request.get_argument("port", is_seq=False, is_qs=False)
        redir_host = self.request.get_argument("redir-host", is_seq=False, is_qs=False)
        redir_port = self.request.get_argument("redir-port", is_seq=False, is_qs=False)

        if not netuitls.is_port_number(port):
            self.finish_with_json({"is_error": True, "message": "错误的服务器端口号值"})
            return

        if not netuitls.is_port_number(redir_port):
            self.finish_with_json({"is_error": True, "message": "错误的重定向端口号值"})
            return

        if not name or not host or not redir_host:
            self.finish_with_json({"is_error": True, "message": "不能存在为空的项"})
            return

        if netuitls.is_ipv6_address(host):
            self.finish_with_json({"is_error": True, "message": "服务器地址不能为IPv6地址"})
            return

        if netuitls.is_ipv6_address(redir_host):
            self.finish_with_json({"is_error": True, "message": "重定向地址不能为IPv6地址"})
            return

        configs = self.sysadm.udp_n2n_configs
        configs[name] = {
            "host": host,
            "port": port,
            "redirect_host": redir_host,
            "redirect_port": redir_port
        }
        self.sysadm.save_udp_n2n_configs()
        self.sysadm.reset_udp_n2n()
        self.finish_with_json({"is_error": False, "message": "添加成功"})

    def del_proxy(self):
        name = self.request.get_argument("name", is_seq=False, is_qs=False)
        configs = self.sysadm.udp_n2n_configs
        if name not in configs:
            self.finish_with_json({"is_error": False, "message": "删除成功"})
            return
        del configs[name]
        self.sysadm.reset_udp_n2n()
        self.finish_with_json({"is_error": False, "message": "删除成功"})

    def handle(self):
        action = self.request.get_argument("action", is_seq=False, is_qs=False)
        if action not in ("add", "del",):
            self.finish_with_json({"is_error": True, "message": "错误的请求动作"})
            return

        if action == "add":
            self.add_proxy()
            return
        self.del_proxy()
