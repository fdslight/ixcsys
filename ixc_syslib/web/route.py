#!/usr/bin/env python3

import os, sys, importlib


class app_route(object):
    def __init__(self):
        pass

    def get_module(self, path_info: str):
        """
        :param path_info:
        :return:
        """
        if path_info != "/" and path_info[-1] == "/":
            path_info = path_info[0:-1]

        if path_info == "/":
            x = "/default"
        else:
            x = path_info

        p = x.find("/staticfiles")
        if p == 0: x = "/staticfiles"

        s = "%s/web.controllers%s" % (os.getenv("IXC_MYAPP_RELATIVE_DIR"), x)
        name = s.replace("/", ".")

        try:
            importlib.import_module(name)
        except ImportError:
            return None

        o = sys.modules[name]
        importlib.reload(o)

        return o

    def __call__(self, environ: dict, start_response):
        path_info = environ["PATH_INFO"]
        m = self.get_module(path_info)

        if not m:
            start_response("404 Not Found", [])
            return []

        rs = m.controller(environ, start_response)
        return rs
