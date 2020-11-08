#!/usr/bin/env python3
"""DNS规则写法
"""

import ixc_syslib.web.controllers.rpc_controller as rpc

from pywind.global_vars import global_vars


class controller(rpc.controller):
    __runtime = None

    def rpc_init(self):
        self.__runtime = global_vars["ixcsys.DNS"]

        self.fobjs = {
            "rule_add": self.rule_add,
            "rule_del": self.rule_del,
            "rule_list": self.rule_list,
        }

    def rule_add(self, host: str, action_name: str, **kwargs):
        """增加DNS规则
        """
        pass

    def rule_del(self, host: str):
        """删除DNS规则
        """
        pass

    def rule_list(self):
        """列出所有DNS规则
        """
        return 0, self.__runtime.matcher.rules
