#!/usr/bin/env python3

import os, sys, importlib, json

BASE_DIR = os.path.dirname(sys.argv[0])

if not BASE_DIR: BASE_DIR = "."

sys.path.append(BASE_DIR)

import pywind.lib.sys_build as sys_build

__builds = [
    "ixc_syscore",
    "ixc_syscore/router",
    "ixc_syscore/sysadm",
    "ixc_syscore/DHCP",
    "ixc_syscore/DNS",
    "ixc_syscore/tftp",
    "ixc_syscore/ip2socks"
]

__helper = """
    help                            show help
    build build_name [cflags]       build software
    build_all [cflags]              build all
    install install_name prefix     install software
    install_all prefix              install all
    show_builds                     show build names
"""


def __read_build_config():
    fpath = "build_config.json"

    if not os.path.isfile(fpath):
        o = {
            "debug": True,
            "c_includes": [
                ""
            ],
            "libs": [
            ],
            "lib_dirs": [

            ]
        }
        return o

    with open(fpath, "r") as f:
        s = f.read()
    f.close()

    o = json.loads(s)

    return o


def __build(args: list):
    if len(args) < 1:
        print("ERROR:please input build_name")
        return

    build_name = args[0]
    if build_name not in __builds:
        print("ERROR:not found build name %s" % build_name)
        return

    name = "%s.make" % build_name.replace("/", ".")

    try:
        importlib.import_module(name)
    except ImportError:
        print("ERROR:not found build name %s make.py file" % build_name)
        return

    cfg = __read_build_config()
    debug = cfg["debug"]
    c_includes = cfg["c_includes"]
    libdirs = cfg["lib_dirs"]
    libs = cfg["libs"]

    m = sys.modules[name]

    if c_includes:
        include = "-I %s " % " ".join(c_includes)
    else:
        include = ""

    if libdirs:
        libdir = "-L %s ".join(libdirs)
    else:
        libdir = ""

    if libs:
        lib = "-l%s ".join(libs)
    else:
        lib = ""

    if debug:
        d = "-g -Wall"
    else:
        d = ""

    cflags = " ".join([d, include, libdir, lib, ])
    cflags = cflags + " " + "".join(args[1:])

    abspath = os.path.abspath(__file__)

    root_dir = os.path.dirname(abspath)

    try:
        m.build(root_dir, "%s/%s" % (root_dir, build_name,), cflags, debug=debug)
    except AttributeError:
        print("ERROR:not found build name %s build method from make.py" % build_name)
        return


def __build_all(args: list):
    pass


def __install(args: list):
    pass


def __install_all(args: list):
    pass


def main():
    if len(sys.argv) < 2:
        print(__helper)
        return

    action = sys.argv[1]
    if action not in ("help", "build", "build_all", "install", "install_all", "show_builds",):
        print(__helper)
        return

    if action == "help":
        print(__helper)
        return

    if action == "build":
        __build(sys.argv[2:])
        return

    if action == "build_all":
        __build_all(sys.argv[2:])
        return

    if action == "install":
        __install(sys.argv[2:])
        return

    if action == "install_all":
        __install_all(sys.argv[2:])
        return

    if action == "show_builds":
        for s in __builds: print(s)
        return


if __name__ == '__main__': main()
