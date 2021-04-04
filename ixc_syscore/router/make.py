#!/usr/bin/env python3

import os, sys, platform
import pywind.lib.sys_build as sys_build


def remove_file(files: list, filename: str):
    results = []

    for x in files:
        p = x.find(filename)
        if p < 0: results.append(x)

    return results


def build(base_dir, my_dir, cflags, debug=True):
    files = sys_build.get_c_files("%s/src" % my_dir)
    #files = remove_file(files, "router.c")
    files += sys_build.get_c_files("%s/pywind/clib/ev" % base_dir)

    if platform.system().lower() == "linux":
        files = remove_file(files, "ev_kqueue.c")

    files += sys_build.get_c_files("%s/pywind/clib" % base_dir)

    if sys.platform.startswith("linux"):
        files += [
            "%s/pywind/clib/netif/linux_tuntap.c" % base_dir,
            "%s/pywind/clib/netif/linux_hwinfo.c" % base_dir,
        ]
    else:
        files += [
            "%s/pywind/clib/netif/freebsd_tuntap.c" % base_dir,
            "%s/pywind/clib/netif/freebsd_hwinfo.c" % base_dir,
        ]

    if debug:
        cflags += " -D DEBUG -rdynamic"
    else:
        cflags += " -O2 -rdynamic -Wall"

    # sys_build.do_compile(files, "%s/pylib/router.so" % my_dir, cflags, is_shared=True)
    sys_build.do_compile(files, "%s/ixc_router_core" % my_dir, cflags)


def install(root_dir, install_root_dir: str, name: str):
    path = "%s/%s" % (install_root_dir, name)
    os.system("mkdir -p %s/%s" % (install_root_dir, name,))
    os.system("cp -r %s/%s/* %s" % (root_dir, name, path))
    os.system("rm -rf %s/src" % path)
    os.system("rm %s/make.py" % path)
