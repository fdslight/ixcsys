#!/usr/bin/env python3

import subprocess
import pywind.lib.sys_build as sys_build


def build(base_dir, mydir, cflags, debug=True):
    files = sys_build.get_c_files("%s/pylib" % mydir)
    files.append(
        "%s/pywind/clib/netutils.c" % base_dir,
    )

    cflags += " -std=gnu11"

    if debug:
        cflags += " -D DEBUG -D _GNU_SOURCE"
    else:
        cflags += " -Wall -D _GNU_SOURCE"

    # sys_build.do_compile(file, "%s/pylib/router.so" % my_dir, cflags, is_shared=True)
    sys_build.do_compile(files, "%s/pylib/racs_cext.so" % mydir, cflags, is_shared=True)


def install(root_dir, install_root_dir: str, name: str):
    path = "%s/%s" % (install_root_dir, name)
    cmds = [
        "mkdir -p %s/%s" % (install_root_dir, name,),
        "cp -r %s/%s/* %s" % (root_dir, name, path),
        "rm %s/pylib/*.c" % path,
        "rm %s/make.py" % path
    ]
    for cmd in cmds: subprocess.call(cmd, shell=True)
