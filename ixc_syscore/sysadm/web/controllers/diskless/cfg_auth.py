#!/usr/bin/env python3
import hashlib

import ixc_syscore.sysadm.web.controllers.controller as base_controller
import pywind.lib.netutils as netutils
from pywind.global_vars import global_vars


class controller(base_controller.BaseController):
    @property
    def sysadm(self):
        return global_vars["ixcsys.sysadm"]

    def init_os_cfg(self):
        return {
            "default_os": None,
            "os_list_wait_timeout": 5,
            "os_list": []
        }

    def myinit(self):
        self.request.set_allow_methods(["POST"])
        return True

    def add_mac(self):
        hwaddr = self.request.get_argument("hwaddr", is_seq=False, is_qs=False)
        cfg_macs = self.sysadm.diskless_cfg_macs

        if not netutils.is_hwaddr(hwaddr):
            self.json_resp(True, "错误的MAC地址格式")
            return

        if hwaddr in cfg_macs:
            self.json_resp(False, None)
            return

        cfg_macs[hwaddr] = self.init_os_cfg()
        self.sysadm.save_diskless_cfg_macs()
        self.json_resp(False, None)

    def del_mac(self):
        hwaddr = self.request.get_argument("hwaddr", is_seq=False, is_qs=False)
        cfg_macs = self.sysadm.diskless_cfg_macs

        if hwaddr not in cfg_macs:
            self.json_resp(False, None)
            return

        del cfg_macs[hwaddr]

        self.sysadm.save_diskless_cfg_macs()
        self.json_resp(False, None)

    def find_user(self, username: str):
        cfg_users = self.sysadm.diskless_cfg_users
        result = {}
        for _dict in cfg_users:
            if _dict["username"] == username:
                result = _dict
                break
            ''''''
        return result

    def add_user(self):
        username = self.request.get_argument("username", is_seq=False, is_qs=False)
        password = self.request.get_argument("password", is_seq=False, is_qs=False)

        if self.find_user(username):
            self.json_resp(True, "用户%s已经存在" % username)
            return

        if not password:
            self.json_resp(True, "密码不能为空")
            return

        md5_pass = hashlib.md5(password.encode()).hexdigest()
        user_cfg = {
            "username": username,
            "password": md5_pass,
            "os_config": self.init_os_cfg()
        }
        cfg_users = self.sysadm.diskless_cfg_users
        cfg_users.append(user_cfg)

        self.sysadm.save_diskless_cfg_users()
        self.json_resp(False, None)

    def mod_user_passwd(self):
        """修改用户密码
        """
        username = self.request.get_argument("username", is_seq=False, is_qs=False)
        password = self.request.get_argument("password", is_seq=False, is_qs=False)

        user_info = self.find_user(username)
        if not user_info:
            self.json_resp(True, "用户%s不存在" % username)
            return

        if not password:
            self.json_resp(True, "密码不能为空")
            return

        md5_pass = hashlib.md5(password.encode()).hexdigest()
        user_info["password"] = md5_pass

        self.sysadm.save_diskless_cfg_users()
        self.json_resp(False, None)

    def del_user(self):
        username = self.request.get_argument("username", is_seq=False, is_qs=False)
        cfg_users = self.sysadm.diskless_cfg_users

        new_configs = []

        for _dict in cfg_users:
            if _dict["username"] != username:
                new_configs.append(_dict)
            else:
                continue
            ''''''
        self.sysadm.diskless_cfg_users = cfg_users
        self.sysadm.save_diskless_cfg_users()

        self.json_resp(False, None)

    def handle(self):
        auth_type = self.request.get_argument("auth_type", is_seq=False, is_qs=False)
        action = self.request.get_argument("action", is_seq=False, is_qs=False)

        cur_auth_type = self.sysadm.diskless_cfg["public"]["auth_type"]
        if cur_auth_type != auth_type:
            self.json_resp(True, "提交的认证类型与当前认证类型不符合")
            return

        if action not in ("add", "delete", "mod_user",):
            self.json_resp(True, "错误的提交动作类型")
            return

        if auth_type == "mac":
            if action == "add":
                self.add_mac()
            else:
                self.del_mac()
            return

        if action == "add":
            self.add_user()
        elif action == "mod_user":
            self.mod_user_passwd()
        else:
            self.del_user()
