#!/usr/bin/env python3

import os
import ixc_syscore.sysadm.web.controllers.controller as base_controller

import ixc_syslib.pylib.RPCClient as RPC


class controller(base_controller.BaseController):
    def myinit(self):
        self.request.set_allow_methods(["POST"])
        return True

    def handle(self):
        mpkt_first_size = self.request.get_argument("mpkt_first_size", is_seq=False, is_qs=False)

        try:
            mpkt_first_size = int(mpkt_first_size)
        except ValueError:
            self.json_resp(True, "提交的不是一个数字，请重新提交")
            return

        self.json_resp(False, "修改小包优先发送临界值成功")
