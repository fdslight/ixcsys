#!/usr/bin/env python3

import ixc_syscore.sysadm.web.controllers.controller as base_controller
import hashlib, json
import ixc_syslib.pylib.RPCClient as RPC


class controller(base_controller.BaseController):
    def myinit(self):
        self.request.set_allow_methods(["POST"])
        return True

    def handle(self):
        passwd_old = self.request.get_argument("passwd_old", is_seq=False, is_qs=False)
        passwd_new1 = self.request.get_argument("passwd_new1", is_seq=False, is_qs=False)
        passwd_new2 = self.request.get_argument("passwd_new2", is_seq=False, is_qs=False)

        if not passwd_old or not passwd_new1 or not passwd_new2:
            self.json_resp(True, "密码不能为空")
            return

        if passwd_new1 != passwd_new2:
            self.json_resp(True, "新密码不一致")
            return

        if len(passwd_new1) < 8:
            self.json_resp(True, "密码不能小于8位")
            return

        fpath = "%s/user.json" % self.my_config_dir

        old_hash = hashlib.md5(passwd_old.encode()).hexdigest()
        new_hash = hashlib.md5(passwd_new1.encode()).hexdigest()

        with open(fpath, "r") as f:
            s = f.read()
        f.close()
        info = json.loads(s)

        if info["password"] != old_hash:
            self.json_resp(True, "错误的旧密码")
            return

        info["password"] = new_hash
        s = json.dumps(info)

        with open(fpath, "w") as f:
            f.write(s)
        f.close()

        self.json_resp(False, {})
