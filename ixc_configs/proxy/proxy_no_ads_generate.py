#!/usr/bin/env python3
# 生成广告屏蔽版本的代理规则文件

import urllib.request

URL = "https://raw.githubusercontent.com/privacy-protection-tools/anti-AD/master/anti-ad-domains.txt"


def main():
    request=urllib.request.Request(URL)
    resp=urllib.request.urlopen(request)

    print(resp.read())


if __name__ == '__main__': main()
