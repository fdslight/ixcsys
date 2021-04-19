#!/usr/bin/env python3

import os
import ixc_syscore.sysadm.web.controllers.controller as base_controller

import ixc_syslib.pylib.RPCClient as RPC


class controller(base_controller.BaseController):
    def myinit(self):
        self.request.set_allow_methods(["POST"])
        return True

    def handle(self):
        file_dir = self.request.get_argument("file_dir", is_seq=False, is_qs=False)

        if not os.path.isdir(file_dir):
            self.json_resp(True, "指定的目录 %s 不是一个目录" % file_dir)
            return

        RPC.fn_call("DHCP", "/dhcp_server", "tftp_dir_set", file_dir)
        RPC.fn_call("DHCP", "/dhcp_server", "save")

        self.json_resp(False, {"file_dir": file_dir})
