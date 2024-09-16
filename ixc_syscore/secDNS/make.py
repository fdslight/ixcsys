#!/usr/bin/env python3
import os


def build(base_dir, mydir, cflags, debug=True):
    pass


def install(root_dir, install_root_dir: str, name: str):
    path = "%s/%s" % (install_root_dir, name)
    os.system("mkdir -p %s/%s" % (install_root_dir, name,))
    os.system("cp -r %s/%s/* %s" % (root_dir, name, path))
    os.system("rm %s/make.py" % path)
