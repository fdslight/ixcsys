#!/usr/bin/env python3

import os
import pywind.web.appframework.handler_ext.staticfile as staticfile


class controller(staticfile.staticfile):
    def get_file_path(self):
        fpath = "%s/web/staticfiles/%s" % (os.getenv("IXC_MYAPP_DIR"), self.request.environ["PATH_INFO"],)

        return fpath
