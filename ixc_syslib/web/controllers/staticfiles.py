#!/usr/bin/env python3
import pywind.web.appframework.handler_ext.staticfile as staticfile


class controller(staticfile.staticfile):
    def staticfile_init(self):
        """重写这个方法
        """
        pass

    def get_file_path(self):
        pass
