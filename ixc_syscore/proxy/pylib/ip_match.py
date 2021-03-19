#!/usr/bin/env python3

import pywind.lib.netutils as netuitls


class ip_match(object):
    __ip_rules = None
    __ipv6_rules = None

    __host_timer = None

    def __init__(self):
        self.__ip_rules = {}
        self.__ipv6_rules = {}

    def __check_format(self, subnet, prefix):
        prefix = int(prefix)
        if prefix < 1: return False

        if netuitls.is_ipv4_address(subnet) and prefix > 32: return False
        if netuitls.is_ipv6_address(subnet) and prefix > 128: return False
        if not netuitls.is_ipv6_address(subnet) and not netuitls.is_ipv4_address(subnet): return False

        return True

    def add_rule(self, subnet, prefix):
        check_rs = self.__check_format(subnet, prefix)
        if not check_rs: return False

        is_ipv6 = False
        if netuitls.is_ipv6_address(subnet): is_ipv6 = True
        if not netuitls.check_ipaddr(subnet, prefix, is_ipv6=is_ipv6): return False

        if is_ipv6:
            subnet = netuitls.calc_subnet(subnet, prefix, is_ipv6=True)
        else:
            subnet = netuitls.calc_subnet(subnet, prefix, is_ipv6=False)

        name = "%s/%s" % (subnet, prefix,)
        if is_ipv6:
            self.__ipv6_rules[name] = (subnet, prefix,)
        else:
            self.__ip_rules[name] = (subnet, prefix,)

        return True

    def match(self, ipaddr, is_ipv6=False):
        if is_ipv6:
            rules = self.__ipv6_rules
        else:
            rules = self.__ip_rules
        result = False

        if is_ipv6:
            n = 128
        else:
            n = 32

        while n > 0:
            subnet = netuitls.calc_subnet(ipaddr, n, is_ipv6=is_ipv6)
            name = "%s/%s" % (subnet, n)
            n -= 1

            if name not in rules: continue
            result = True
            break

        return result

    def clear(self):
        self.__ip_rules = {}
        self.__ipv6_rules = {}
