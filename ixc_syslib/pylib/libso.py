#!/usr/bin/env python3

import os


def parse_linux_deps(file_path: str):
    fd = os.popen("ldd %s" % file_path)
    results = []

    for line in fd:
        s = line.replace("\r", "")
        s = s.replace("\t", "")
        s = s.replace("\n", "")

        p = s.find("=>")
        if p < 1: continue
        so_name = s[0:p].strip()
        p += 2
        so_path = s[p:].strip()
        p = so_path.find("(0x")
        so_path = so_path[0:p].strip()
        results.append((so_name, so_path,))

    fd.close()
    return results
