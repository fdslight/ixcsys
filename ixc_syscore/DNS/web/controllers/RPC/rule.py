#!/usr/bin/env python3
"""DNS规则写法
"""

import pywind.lib.netutils as netutils
import ixc_syslib.web.controllers.rpc_controller as rpc
import ixc_syslib.pylib.RPCClient as RPC

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

    def add(self, host: str, action_name: str, priv_data=None):
        """增加DNS规则
        """
        if not isinstance(action_name, str):
            return RPC.ERR_ARGS, "wrong action_name argument type"
        self.__runtime.matcher.add_rule(host, action_name, priv_data=priv_data)
        return 0, None

    def delete(self, host: str):
        """删除DNS规则
        """
        self.__runtime.matcher.del_rule(host)
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
        if not netutils.is_port_number(port):
            return RPC.ERR_ARGS, "wrong port number value" % port
        self.__runtime.rule_forward_set(port)

        return 0, None
