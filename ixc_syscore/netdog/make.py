#!/usr/bin/env python3

import os, platform, sys
import pywind.lib.sys_build as sys_build


def remove_file(files: list, filename: str):
    results = []

    for x in files:
        p = x.find(filename)
        if p < 0: results.append(x)

    return results


def build(base_dir, mydir, cflags, debug=True):
    files = sys_build.get_c_files("%s/src" % mydir)
    files += sys_build.get_c_files("%s/src/anylize" % mydir)

    files += sys_build.get_c_files("%s/pywind/clib/ev" % base_dir)

    if platform.system().lower() == "linux":
        files = remove_file(files, "ev_kqueue.c")

    files += sys_build.get_c_files("%s/pywind/clib" % base_dir)

    cflags += " -std=gnu11"

    if debug:
        cflags += " -D DEBUG -D _GNU_SOURCE"
    else:
        cflags += " -O3 -Wall -D _GNU_SOURCE"

    # sys_build.do_compile(file, "%s/pylib/router.so" % my_dir, cflags, is_shared=True)
    sys_build.do_compile(files, "%s/ixc_netdog_anylized" % mydir, cflags)


def install(root_dir, install_root_dir: str, name: str):
    path = "%s/%s" % (install_root_dir, name)
    os.system("mkdir -p %s/%s" % (install_root_dir, name,))
    os.system("cp -r %s/%s/* %s" % (root_dir, name, path))
    os.system("rm %s/make.py" % path)