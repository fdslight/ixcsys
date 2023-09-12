#!/usr/bin/env python3
# 核对主机规则

class host_match(object):
    """对域名进行匹配,以找到是否在符合的规则列表中
    """
    __domain_rules = None

    def __init__(self):
        self.__domain_rules = {}

    def add_rule(self, host_rule):
        host, flags = host_rule
        tmplist = host.split(".")
        tmplist.reverse()

        if not tmplist: return

        lsize = len(tmplist)
        n = 0
        tmpdict = self.__domain_rules

        old_name = ""
        old_dict = tmpdict
        while n < lsize:
            name = tmplist[n]
            if name not in tmpdict:
                if name == "*" or n == lsize - 1:
                    old_dict[old_name] = {name: flags}
                    break
                old_dict = tmpdict
                tmpdict[name] = {}
            if name == "*":
                n += 1
                continue
            old_name = name
            tmpdict = tmpdict[name]
            n += 1

        return

    def match(self, host):
        tmplist = host.split(".")
        tmplist.reverse()
        # 加一个空数据，用以匹配 xxx.xx这样的域名
        tmplist.append("")

        is_match = False
        flags = 0

        tmpdict = self.__domain_rules
        for name in tmplist:
            if "*" in tmpdict:
                is_match = True
                flags = tmpdict["*"]
                break
            if name not in tmpdict: break
            v = tmpdict[name]
            if type(v) != dict:
                is_match = True
                flags = v
                break
            tmpdict = v

        return (is_match, flags,)

    def clear(self):
        self.__domain_rules = {}


class FilefmtErr(Exception): pass


def __drop_comment(line):
    """删除注释"""
    pos = line.find("#")
    if pos < 0:
        return line
    return line[0:pos]


def __read_from_file(fpath):
    result = []
    fdst = open(fpath, "rb")

    for line in fdst:
        line = line.decode("iso-8859-1")
        line = __drop_comment(line)
        line = line.replace("\r", "")
        line = line.replace("\n", "")
        line = line.lstrip()
        line = line.rstrip()
        if not line: continue
        result.append(line)
    fdst.close()

    return result


def parse_host_file(fpath):
    """解析主机文件,即域名规则文件"""
    lines = __read_from_file(fpath)
    results = []
    for line in lines:
        find = line.find(":")
        if find < 1: raise FilefmtErr("wrong host_rule content %s" % line)
        a = line[0:find]
        e = find + 1
        try:
            b = int(line[e:])
        except ValueError:
            raise FilefmtErr("wrong host_rule content %s" % line)
        results.append((a, b,))
    return results


def check():
    fpath = "proxy_domain.txt"
    rules = parse_host_file(fpath)
    matcher = host_match()

    for rule in rules:
        is_match, flags = matcher.match(rule[0])

        if is_match:
            print("conflict rule %s" % rule[0])
            continue

        matcher.add_rule(rule)
    return


def main():
    print("------------------check start------------------")
    check()
    print("------------------check finish-----------------")


if __name__ == '__main__': main()
