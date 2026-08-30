#!/usr/bin/env python3
"""DNS规则写法
"""

import pywind.lib.netutils as netutils
import ixc_syslib.web.controllers.rpc_controller as rpc
import ixc_syslib.pylib.RPCClient as RPC
from DNS.pylib.rule import matcher

from pywind.global_vars import global_vars


class controller(rpc.controller):
    __runtime = None

    def rpc_init(self):
        self.__runtime = global_vars["ixcsys.DNS"]

        self.fobjs = {
            "add": self.add,
            "adds": self.adds,
            "del": self.delete,
            "list": self.list,
            "set_forward": self.set_forward,
            "get_forward": self.get_forward,
            "clear": self.clear,
            "sec_rule_add": self.sec_rule_add,
            "sec_rules_add": self.sec_rules_add,
            "sec_rule_del": self.sec_rule_del,
            "sec_rules_del": self.sec_rules_del,
            "sec_rules_modify": self.sec_rules_modify,
            "sec_rules_modify_with_raw": self.sec_rules_modify_with_raw,
            "sec_rules_modify_with_fpath": self.sec_rules_modify_with_fpath,
            "get_sec_rules": self.get_sec_rules,

            "dbg_rule_match": self.dbg_rule_match,
            "dbg_rule_show": self.dbg_rule_show,
        }

    def dbg_rule_match(self, host: str):
        return 0, self.__runtime.matcher.match(host)

    def dbg_rule_show(self):
        return 0, self.__runtime.matcher.rules

    def add(self, host: str, action_name: str, priv_data=None):
        """增加DNS规则
        """
        if not isinstance(action_name, str):
            return RPC.ERR_ARGS, "wrong action_name argument type"
        return 0, self.__runtime.matcher.add_rule(host, action_name, priv_data=priv_data)

    def adds(self, hosts: list):
        for host, action in hosts:
            self.add(host, action)
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

    def clear(self):
        self.__runtime.rule_clear()
        return 0, None

    def set_forward(self, port: int):
        """设置重定向服务器
        :param port:
        :return:
        """
        if not netutils.is_port_number(port):
            return RPC.ERR_ARGS, "wrong port number value" % port
        self.__runtime.rule_forward_set(port)

        return 0, None

    def get_forward(self):
        """获取DNS服务器的转发端口
        :return:
        """
        return 0, self.__runtime.get_forward()

    def sec_rule_add(self, rule: str):
        self.__runtime.add_sec_rule(rule)

        return 0, None

    def sec_rules_add(self, rules: list):
        self.__runtime.add_sec_rules(rules)
        return 0, None

    def sec_rule_del(self, rule: str):
        self.__runtime.del_sec_rule(rule)

        return 0, None

    def sec_rules_del(self, rules: list):
        self.__runtime.del_sec_rules(rules)

        return 0, None

    def sec_rules_modify(self, rules: list):
        self.__runtime.sec_rules_modify(rules)

        return 0, None

    def sec_rules_modify_with_raw(self, text: bytes, is_compressed=False):
        self.__runtime.sec_rules_modify_with_raw(text, is_compressed=is_compressed)

        return 0, None

    def sec_rules_modify_with_fpath(self, fpath: str):
        self.__runtime.sec_rules_modify_with_fpath(fpath)

        return 0, None

    def get_sec_rules(self):
        return 0, self.__runtime.sec_rules
