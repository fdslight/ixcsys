#!/usr/bin/env python3

import sys

sys.path.append("../../")

import pywind.lib.sys_build as sys_builder


def main():
    files = [
        "src/cweb.c"
    ]
    sys_builder.do_compile(files,"ixcweb.exe","-DDEBUG")


if __name__ == '__main__': main()
