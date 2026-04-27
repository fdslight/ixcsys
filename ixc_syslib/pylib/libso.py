#!/usr/bin/env python3

import os, subprocess


def parse_linux_deps(file_path: str):
    rs = subprocess.run("ldd %s" % file_path, capture_output=True, shell=True)
    lib_list = rs.stdout.decode().split("\n")

    results = []

    for line in lib_list:
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

    return results
