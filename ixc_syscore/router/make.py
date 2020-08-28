#!/usr/bin/env python3

import os
import pywind.lib.sys_build as sys_build


def build(base_dir, my_dir, cflags, debug=True):
    files = sys_build.get_c_files("%s/src" % my_dir)
    files += [
        "%s/pylib/router.c" % my_dir
    ]

    if debug: cflags += " -D DEBUG"

    sys_build.do_compile(files, "%s/pylib/router.so" % my_dir, cflags, is_shared=True)


def install(mydir, prefix):
    pass
