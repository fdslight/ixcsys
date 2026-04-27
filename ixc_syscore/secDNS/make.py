#!/usr/bin/env python3
import subprocess


def build(base_dir, mydir, cflags, debug=True):
    pass


def install(root_dir, install_root_dir: str, name: str):
    path = "%s/%s" % (install_root_dir, name)
    cmds = [
        "mkdir -p %s/%s" % (install_root_dir, name,),
        "cp -r %s/%s/* %s" % (root_dir, name, path),
        "rm %s/make.py" % path,
    ]
    for cmd in cmds: subprocess.call(cmd, shell=True)
