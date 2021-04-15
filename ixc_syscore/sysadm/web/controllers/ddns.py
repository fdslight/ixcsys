#!/usr/bin/env python3

import ixc_syscore.sysadm.web.controllers.controller as base_controller

from pywind.global_vars import global_vars


class controller(base_controller.BaseController):
    def myinit(self):
        self.request.set_allow_methods(["POST"])
        return True

    @property
    def sysadm(self):
        return global_vars["ixcsys.sysadm"]

    def handle(self):
        enable = self.request.get_argument("enable", is_seq=False, is_qs=False)
        email = self.request.get_argument("email", is_seq=False, is_qs=False)
        api_key = self.request.get_argument("api_key", is_seq=False, is_qs=False)
        sync_interval = self.request.get_argument("sync_interval", is_seq=False, is_qs=False)
        domain = self.request.get_argument("domain", is_seq=False, is_qs=False)

        if enable and (not email or not api_key or not sync_interval or not domain):
            self.json_resp(True, "不能存在为空的内容")
            return

        if not enable:
            self.sysadm.cloudflare_ddns_set("", "", "", 180, enable=False)
            self.json_resp(False, "")
            return

        try:
            sync_interval = int(sync_interval)
        except ValueError:
            self.json_resp(True, "错误的同步时间值")
            return

        if sync_interval < 180:
            self.json_resp(True, "同步时间至少需要180秒")
            return

        self.sysadm.cloudflare_ddns_set(email, api_key, domain, sync_interval, enable=True)
        self.json_resp(False, "")
