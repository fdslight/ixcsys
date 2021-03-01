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
            "add": self.add,
            "del": self.delete,
            "list": self.list,
        }

    def add(self, host: str, action_name: str, **kwargs):
        """增加DNS规则
        """
        return 0, None

    def delete(self, host: str):
        """删除DNS规则
        """
        return 0, None

    def list(self):
        """列出所有DNS规则
        """
        return 0, self.__runtime.matcher.rules

    def set_forward(self, port: int):
        """设置重定向服务器
        :param port:
        :return:
        """
        return 0, None
