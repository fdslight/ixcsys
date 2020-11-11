#!/usr/bin/env python3

import ixc_syscore.sysadm.web.controllers.controller as base_controller


class controller(base_controller.BaseController):
    def myinit(self):
        self.request.set_allow_methods(["GET", "POST"])
        return True

    def signin(self, user_name: str):
        pass

    def handle_get(self):
        self.render("signin.html")

    def handle_post(self):
        username = self.request.get_argument("username", is_qs=False, is_seq=False)
        passwd = self.request.get_argument("passwd", is_qs=False, is_seq=False)

        if not username or not passwd:
            self.finish_with_json({"is_ok": False, "error_name": "username_or_passwd_emptys"})
            return
        self.finish_with_json({"is_ok": True})

    def handle(self):
        method = self.request.environ["REQUEST_METHOD"]
        if method == "GET":
            self.handle_get()
        else:
            self.handle_post()
