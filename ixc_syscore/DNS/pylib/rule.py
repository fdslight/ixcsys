#!/usr/bin/env python3
"""规则匹配
书写格式如下:

1.匹配所有的子域名
*.example1.com
2.匹配单个子域名
www.example.com

action规则是一个Python字典对象,规则如下
1.重定向
{"action":"forward"}
2.重定向以及自动设置路由到指定程序端口
{"action":"forward_and_auto_route"}
3.丢弃该DNS请求
{"action":"drop"}
4.重写DNS记录,该动作目前未实现,保留
{"action":"rewrite","DNS":{"MX":"","A":""}}
"""

action_names = [
    "forward", "forward_and_auto_route", "drop", "rewrite"
]


class matcher(object):
    __rule_tree = None
    __rules = None

    def __init__(self):
        self.__cb_flags = False
        self.__rule_tree = {}
        self.__rules = {}

    def match(self, host: str, cb_flags=False):
        """匹配主机
        """
        _list = host.split(".")
        _list.reverse()

        o = self.__rule_tree
        is_found = True
        for x in _list:
            if x not in o:
                is_found = False
                break
            o = o[x]
        if is_found: return o["action"]
        if not cb_flags:
            # 找不到那么替换子域名重新匹配一次
            _list = host.split(".")
            _list[0] = "*"
            return self.match(".".join(_list), cb_flags=True)
        return None

    def add_rule(self, rule: str, action: dict):
        """加入规则
        :param rule,规则
        :param action
        :return Boolean,添加成功那么返回True,不存在则返回False
        """
        if rule in self.__rules: return False
        _list = rule.split(".")
        _list.reverse()
        o = self.__rule_tree

        for x in _list:
            # 新建的引用计数为0
            if x not in o: o[x] = {"refcnt": 0, "action": None}
            o = o[x]
            o["refcnt"] += 1
        o["action"] = action
        self.__rules[rule] = None
        return True

    def del_rule(self, rule: str):
        """删除规则
        :return Boolean,删除成功那么返回True,不存在则返回False
        """
        if rule not in self.__rules: return False

        _list = rule.split(".")
        _list.reverse()

        o = self.__rule_tree
        is_found = True

        for x in _list:
            if x not in o:
                is_found = False
                break
            o = o[x]
        if not is_found: return

        o = self.__rule_tree

        for x in _list:
            t = o
            o = o[x]
            o["refcnt"] -= 1
            if o["refcnt"] == 0:
                del t[x]
                break
            ''''''
        del self.__rules[rule]
        return True

    @property
    def rule_tree(self):
        return self.__rule_tree

    @property
    def rules(self):
        rules = []
        for x in self.__rules: rules.append(x)
        return rules

    def exists(self, rule: str):
        """检查规则是否存在
        """
        return rule in self.__rules


"""
cls = matcher()
cls.add_rule("www.google.com", "xxx")
cls.add_rule("*.google.com", "this is action")
# print(cls.rules)
# print(cls.rule_tree)
print(cls.match("www.google.com"))
"""
