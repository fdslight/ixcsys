#!/usr/bin/env python3

import hashlib
import ixc_syscore.sysadm.web.controllers.controller as base_controller
import ixc_syslib.pylib.RPCClient as RPC


class controller(base_controller.BaseController):
    def myinit(self):
        self.request.set_allow_methods(["GET", "POST"])
        return True

    def handle_get(self):
        if not self.is_signed():
            self.render("signin.html")
            return
        page = self.request.get_argument("page", default=None, is_qs=True, is_seq=False)
        if not page: page = "default"
        cur_internet_type = RPC.fn_call("router", "/config", "cur_internet_type_get")
        self.render("homepage.html", page=page, cur_internet_type=cur_internet_type)

    def handle_post(self):
        username = self.request.get_argument("username", is_qs=False, is_seq=False)
        passwd = self.request.get_argument("passwd", is_qs=False, is_seq=False)

        if not username or not passwd:
            self.finish_with_json({"is_ok": False, "error_name": "username_or_passwd_empty"})
            return

        user_info = self.user_configs
        if user_info["user"] != username:
            self.finish_with_json({"is_ok": False, "error_name": "wrong_username_or_passwd"})
            return

        hash_pass = hashlib.md5(passwd.encode()).hexdigest()

        if hash_pass != user_info["password"]:
            self.finish_with_json({"is_ok": False, "error_name": "wrong_username_or_passwd"})
            return
        self.signin(username)
        self.finish_with_json({"is_ok": True})

    def handle(self):
        method = self.request.environ["REQUEST_METHOD"]
        if method == "GET":
            self.handle_get()
        else:
            self.handle_post()
