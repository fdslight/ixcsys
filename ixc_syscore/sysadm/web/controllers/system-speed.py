#!/usr/bin/env python3

import ixc_syscore.sysadm.web.controllers.controller as base_controller

import ixc_syslib.pylib.RPCClient as RPC


class controller(base_controller.BaseController):
    def myinit(self):
        self.request.set_allow_methods(["POST"])
        return True

    def handle(self):
        bind_cpu = self.request.get_argument("bind_cpu", is_seq=False, is_qs=False)
        system_cpus = RPC.fn_call("router", "/config", "cpu_num")
        system_cpus = int(system_cpus)

        try:
            bind_cpu = int(bind_cpu)
        except ValueError:
            self.json_resp(True, "wrong submit bind cpu value")
            return

        if bind_cpu >= system_cpus:
            self.json_resp(True, "wrong submit bind cpu value")
            return

        RPC.fn_call("router","/config", "bind_cpu", bind_cpu)
        self.json_resp(False, {})
