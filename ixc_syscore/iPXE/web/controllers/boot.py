#!/usr/bin/env python3

import ixc_syscore.sysadm.web.controllers.controller as base_controller


class controller(base_controller.BaseController):
    def myinit(self):
        self.set_auto_auth(False)
        self.request.set_allow_methods(["GET"])
        return True

    def handle(self):
        boot_file_path = "%s/data/boot.php" % self.my_app_dir
        with open(boot_file_path, "rb") as f:
            byte_s = f.read()
        f.close()
        self.finish_with_bytes("application/octet-stream", byte_s)
