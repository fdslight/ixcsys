#!/usr/bin/env python3

import pywind.lib.timer as timer
import ixc_syslib.pylib.dns_utils as dns_utils


class DNSCache(object):
    __cache_A = None
    __cache_AAAA = None

    def __init__(self):
        self.__cache_A = {}
        self.__cache_AAAA = {}

    def set_expire_time(self, secs: int):
        """设置缓存过期时间
        """
        pass
