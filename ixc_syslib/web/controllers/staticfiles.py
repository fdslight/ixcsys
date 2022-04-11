#!/usr/bin/env python3
import pywind.web.appframework.handler_ext.staticfile as staticfile
import os
import ixc_syslib.pylib.logging as logging


class controller(staticfile.staticfile):
    def staticfile_init(self):
        """重写这个方法
        """
        pass

    def get_file_path(self):
        path_info = self.request.environ["PATH_INFO"]
        file_path = "%s/web%s" % (os.getenv("IXC_MYAPP_RELATIVE_DIR"), path_info)

        return file_path
