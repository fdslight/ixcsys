#!/usr/bin/env python3
# 规则配置更新相关库

import os


def get_internet_proxy_domain_rules():
    """获取internet代理规则
    """
    dst_path = "/tmp/proxy_domain.txt"
    url = "https://raw.githubusercontent.com/fdslight/ixcsys/master/ixc_configs/proxy/proxy_domain.txt"
    os.system("wget %s -o %s" % (url, dst_path,))

    if not os.path.isfile(dst_path):
        return None

    with open(dst_path, "r") as f:
        s = f.read()
    f.close()

    return s


def get_internet_proxy_ip_rules():
    """获取internet代理IP规则
    """
    dst_path = "/tmp/proxy_ip.txt"
    url = "https://raw.githubusercontent.com/fdslight/ixcsys/master/ixc_configs/proxy/proxy_ip.txt"
    os.system("wget %s -o %s" % (url, dst_path,))

    if not os.path.isfile(dst_path):
        return None

    with open(dst_path, "r") as f:
        s = f.read()
    f.close()

    return s


def get_internet_pass_ip_rules():
    """获取直通IP规则
    """
    dst_path = "/tmp/pass_ip.txt"
    url = "https://github.com/fdslight/ixcsys/blob/master/ixc_configs/proxy/pass_ip.txt"
    os.system("wget %s -o %s" % (url, dst_path,))

    if not os.path.isfile(dst_path):
        return None

    with open(dst_path, "r") as f:
        s = f.read()
    f.close()

    return s


def get_dns_sec_rules():
    dst_path = "/tmp/sec_dns_rules.txt"

    if not os.path.isfile(dst_path):
        return None

    with open(dst_path, "r") as f:
        s = f.read()
    f.close()

    return s