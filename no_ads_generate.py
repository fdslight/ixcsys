#!/usr/bin/env python3
# 生成DNS广告屏蔽规则

import os

URL = "https://raw.githubusercontent.com/privacy-protection-tools/anti-AD/refs/heads/master/anti-ad-domains.txt"

# 核外加入的匹配规则
EXTRA_ADDS = [
    "*.gz-data.com",
]

# 去除一些规则
EXTRA_DROPS = [
    "google",
    "twitter",
    "facebook",
    "microsoft",
    "bing",
    ".qy.net",
 #   "doubleclick.net",
 #   "doubleclick.com",
    "sentry.io",
    "app-measurement",
    "cloudflare.com",
    ".stripe.com",
    ".tw",
    ".philips.",
    ".cloudfront.net",
    "amazonaws.com",
    ".amazon.",
    "americanexpress",
    ".windows.com",
    ".yahoo.com",
    ".yandex.ru",
    ".co.jp",
    ".dyson.",
    ".reddit.com",
    ".redditmedia.com",
    ".redhat.com",
    ".ricoh.",
    "marketo.net",

    "simba.taobao.com",
    "ganjing",
    "xiaohongshu.com",

    # 去除规则,避免和额外加入的重复
    "gz-data.com",
    # 允许p2p
    "p2p"
]


def parse(fpath: str):
    fdst = open(fpath, "r")
    results = []

    for line in fdst:
        line = line.strip()
        line = line.replace("\n", "")
        line = line.replace("\r", "")
        if not line: continue
        if line[0] == "#": continue

        is_matched = False
        for s in EXTRA_DROPS:
            p = line.find(s)
            if p >= 0:
                is_matched = True
                break
            ''''''
        if is_matched: continue

        results.append(line)
    fdst.close()
    return results


def gen_dns_rule(results):
    """生成DNS屏蔽规则
    """
    fname = "DNS_NO_ADS_RULES.txt"
    fdst = open(fname, "w")

    for host in EXTRA_ADDS:
        fdst.write("%s\r\n" % host)

    for host in results:
        fdst.write("%s\r\n" % host)

    fdst.close()
    print("generate DNS NO AD rule file %s OK" % fname)


def main():
    fname = "anti-ad-domains.txt"
    if os.path.isfile(fname): os.remove(fname)
    os.system("wget %s --no-check-certificate" % URL)
    results = parse(fname)
    # gen_proxy_rule(results)
    gen_dns_rule(results)
    os.remove(fname)


if __name__ == '__main__': main()
