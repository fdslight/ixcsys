#!/usr/bin/env python3

import os
import ixc_syscore.sysadm.web.controllers.controller as base_controller

import ixc_syslib.pylib.RPCClient as RPC


class controller(base_controller.BaseController):
    def myinit(self):
        self.request.set_allow_methods(["POST"])
        return True

    def handle(self):
        enable = self.request.get_argument("enable", is_seq=False, is_qs=False)
        dest_ip = self.request.get_argument("dest_ip", is_seq=False, is_qs=False)
        old_src_ip = self.request.get_argument("old_src_ip", is_seq=False, is_qs=False)
        new_src_ip = self.request.get_argument("new_src_ip", is_seq=False, is_qs=False)

        self.json_resp(False, {})
