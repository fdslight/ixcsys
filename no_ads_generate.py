#!/usr/bin/env python3
# 生成广告屏蔽版本的代理规则文件
import os

URL = "https://raw.githubusercontent.com/privacy-protection-tools/anti-AD/master/anti-ad-domains.txt"


def parse(fpath: str):
    fdst = open(fpath, "r")
    results = []

    for line in fdst:
        line = line.strip()
        line = line.replace("\n", "")
        line = line.replace("\r", "")
        if not line: continue
        if line[0] == "#": continue

        if line.find("google") >= 0: continue
        if line.find("twitter") >= 0: continue
        if line.find("facebook") >= 0: continue

        results.append(line)
    fdst.close()
    return results


def gen_dns_rule(results):
    """生成DNS屏蔽规则
    """
    fname = "dns_no_ads.txt"
    fdst = open(fname, "w")
    for host in results:
        fdst.write("%s\r\n" % host)

    fdst.close()
    print("generate DNS NO AD rule file %s OK" % fname)


def main():
    fname = "anti-ad-domains.txt"
    if os.path.isfile(fname): os.remove(fname)
    os.system("wget %s" % URL)
    results = parse(fname)
    # gen_proxy_rule(results)
    gen_dns_rule(results)
    os.remove(fname)


if __name__ == '__main__': main()
