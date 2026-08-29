#!/usr/bin/env python3
# https://github.com/blackmatrix7/ios_rule_script/blob/master/rule/Clash/ChinaMax/ChinaMax_Domain.txt

import subprocess, os, time


def generate(src_path, dst_path, adds: list, suffix):
    up_time = time.strftime("# %Y-%m-%d %H:%M:%S\n")
    dst = open(dst_path, "w")
    dst.write(up_time)

    s = """### --------------重要说明--------------------------

## 域名前缀的"*"表示匹配所有,"#"开头的表示注释
# ":0" 表示DNS走加密
# ":1" 表示解析DNS并且走代理
# ":2" 表示DNS不走代理,可与规则"*:1"配合使用,实现规则外全部走代理
# 如果配置"*:1"规则时,需要额外增加一条“your_proxy_domain:2”,让你自己的域名不走代理,否则会造成无法连接代理服务器

###-------------------------------------------------
"""
    dst.write(s)
    dst.write("\n")

    for name, value in adds:
        dst.write(name + ":" + str(value) + "\n")
    dst.write("\n")

    src = open(src_path, 'r')
    for line in src:
        line = line.strip()
        line = line.replace('\n', '')
        line = line.replace('\r', '')
        if not line: continue
        if line[0] == "#":
            dst.write(line + "\n")
            continue
        if line[0] == ".":
            new_line = "*" + line + ":%s" % suffix + "\n"
        else:
            new_line = line + ":%s" % suffix + "\n"
        dst.write(new_line)
    src.close()
    dst.close()

    print("generate file %s OK" % dst_path)


def main():
    fname = "chinamax_domain.txt"
    if os.path.isfile(fname): os.remove(fname)

    url = "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/refs/heads/master/rule/Clash/ChinaMax/ChinaMax_Domain.txt"

    subprocess.call("curl %s -o chinamax_domain.txt" % url, shell=True)
    ext_rules = [
        ("*", 1),
    ]
    generate("chinamax_domain.txt", "proxy_domain.txt", ext_rules, "2")


if __name__ == "__main__":
    main()
