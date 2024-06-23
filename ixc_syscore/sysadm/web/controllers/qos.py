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

        if mpkt_first_size != 0:
            if mpkt_first_size < 64 or mpkt_first_size > 512:
                self.json_resp(True, "非法的小包临界值数值,数值为0或者64到512字节之间")
                return
            ''''''

        RPC.fn_call("router", "/config", "port_map_del", mpkt_first_size)

        self.json_resp(False, "修改小包优先发送临界值成功")
