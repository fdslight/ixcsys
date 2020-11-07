#!/usr/bin/env python3
"""规则匹配
书写格式如下:

1.匹配所有的子域名
*.example1.com
"""


class matcher(object):
    __rule_tree = None
    __rules = None

    def __init__(self):
        self.__rule_tree = {}
        self.__rules = {}

    def match(self, host: str):
        """匹配主机
        """
        _list = host.split(".")
        _list.reverse()

    def add_rule(self, rule: str, action):
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


cls = matcher()
cls.add_rule("x|y|z.google.com", "xxx")
cls.add_rule("chrome.google.com", "this is action")
# print(cls.rules)
# print(cls.rule_tree)
print(cls.match("chrome.google.com"))
