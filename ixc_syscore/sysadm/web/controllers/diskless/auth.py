#!/usr/bin/env python3
import hashlib
import ixc_syscore.sysadm.web.controllers.controller as base_controller
from pywind.global_vars import global_vars


class controller(base_controller.BaseController):
    def myinit(self):
        self.request.set_allow_methods(["GET"])
        return True

    @property
    def sysadm(self):
        return global_vars["ixcsys.sysadm"]

    def send_script(self, script: str):
        self.finish_with_bytes("application/octet-stream", script.encode())

    def send_os_list(self, auth_type: str, k: str, passwd=None):
        """发送操作系统列表
        """
        if auth_type == "mac":
            os_list = self.sysadm.diskless_os_cfg_get(k, is_mac_auth=True)
        else:
            os_list = self.sysadm.diskless_os_cfg_get(k, is_mac_auth=False, password=passwd)
        _list = ["#!ipxe", "\n", ]


    def send_login_ui(self):
        """发送登录UI
        """
        _list = ["#!ipxe", "\n", "login",
                 "chain http://${next-server}/sysadm/auth?flags=1&username=${username}&password=${password}"]
        self.send_script("\n".join(_list))

    def send_exit(self, reason=None):
        """发送退出
        """
        pass

    def handle(self):
        cur_auth_type = self.sysadm.diskless_cfg["public"]["auth_type"]
        flags = self.request.get_argument("flags", is_seq=False, is_qs=True)

        if cur_auth_type == "mac":
            hwaddr = self.request.get_argument("hwaddr", is_seq=False, is_qs=True)
            self.send_os_list("mac", hwaddr)
            return

        if not flags:
            self.send_login_ui()
            return

        username = self.request.get_argument("username", is_seq=False, is_qs=True)
        passwd = self.request.get_argument("password", is_seq=False, is_qs=True)

        if not username or not passwd:
            self.send_exit(reason="user not exists or password wrong")
            return

        md5_pass = hashlib.md5(passwd.encode()).hexdigest()
        self.send_os_list("account", username, passwd=md5_pass)
