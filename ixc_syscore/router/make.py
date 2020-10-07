#!/usr/bin/env python3

import os, sys
import pywind.lib.sys_build as sys_build


def build(base_dir, my_dir, cflags, debug=True):
    files = sys_build.get_c_files("%s/src" % my_dir)
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

    files += [
        "%s/pylib/router.c" % my_dir
    ]

    if debug:
        cflags += " -D DEBUG -rdynamic"
    else:
        cflags += " -O2 -rdynamic"

    sys_build.do_compile(files, "%s/pylib/router.so" % my_dir, cflags, is_shared=True)


def install(mydir, prefix):
    pass
