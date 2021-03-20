#!/usr/bin/env python3

import os


def get_crypto_modules():
    path = os.path.dirname(__file__)
    dirs = os.listdir(path)

    modules = []

    for dir in dirs:
        if dir[0] == "_": continue
        tmp_path = "%s/%s" % (path, dir,)
        if not os.path.isdir(tmp_path): continue
        modules.append(dir)

    return modules
