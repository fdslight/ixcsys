#!/usr/bin/env python3
"""规则匹配
书写格式如下:

1.匹配所有的子域名
*.example1.com

"""

class matcher(object):
    __rules = None

    def __init__(self):
        self.__rules = {}

    def match(self, domain: str):
        """匹配域名
        """
        pass

    def add_rule(self, rule: str, action: int):
        """加入规则
        :param rule,规则
        :param action
        """
        pass

    def del_rule(self, rule: str):
        """删除规则
        """
        pass

    @property
    def rules(self):
        return self.__rules
