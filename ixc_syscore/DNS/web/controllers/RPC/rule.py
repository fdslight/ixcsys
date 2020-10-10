#!/usr/bin/env python3

import ixc_syslib.web.controllers.rpc_controller as rpc

from pywind.global_vars import global_vars


class controller(rpc.controller):
    __runtime = None

    def rpc_init(self):
        self.__runtime = global_vars["ixcsys.DNS"]

        self.fobjs = {
        }

    def rule_add(self, rule: str, action: str):
        """增加DNS规则
        """
        pass

    def rule_del(self, rule: str):
        """删除DNS规则
        """
        pass

    def rule_list(self):
        """列出所有DNS规则
        """
        pass
