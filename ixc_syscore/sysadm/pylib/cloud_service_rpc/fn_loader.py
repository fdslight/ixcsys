#!/usr/bin/env python3
"""函数加载器
"""


class LoaderErr(Exception):
    pass


# 未发生故障
ERR_NO = 0
# 命名空间未找到
ERR_NS_NOT_FOUND = 1
# 函数未找到
ERR_FN_NOT_FOUND = 2
# 参数错误
ERR_FN_ARGS = 3
# 系统错误
ERR_SYS = 4

import importlib


class loader(object):
    def __init__(self):
        pass

    def import_module(self, namespace: str):
        pass

    def call_function(self, namespace: str, fn_name: str, *args, **kwargs):
        pass
