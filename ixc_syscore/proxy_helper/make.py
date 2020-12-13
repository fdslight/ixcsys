#!/usr/bin/env python3

import pywind.lib.sys_build as sys_build

def build(base_dir, mydir, cflags, debug=True):
    files = sys_build.get_c_files("%s/src" % mydir)
    files += sys_build.get_c_files("%s/pywind/clib" % base_dir)

    files += [
        "%s/pylib/proxy_helper.c" % mydir
    ]

    if debug:
        cflags += " -D DEBUG -rdynamic"
    else:
        cflags += " -O2 -rdynamic"

    sys_build.do_compile(files, "%s/pylib/proxy_helper.so" % mydir, cflags, is_shared=True)


def install(mydir, prefix):
    pass
