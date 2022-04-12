#!/usr/bin/env python3

import pywind.web.appframework.handler_ext.staticfile as staticfile
import os

class controller(staticfile.staticfile):
    def staticfile_init(self):
        """重写这个方法
        """
        self.set_mime("map", "application/json;charset=utf-8")
        self.set_no_cache()

    def get_file_path(self):
        path_info = self.request.environ["PATH_INFO"]
        file_path = "%s/web%s" % (os.getenv("IXC_MYAPP_RELATIVE_DIR"), path_info)

        # 解决偶发的无法找到静态文件的BUG
        if not os.path.isfile(file_path):
            file_path = "/opt/ixcsys/ixc_syscore/sysadm/web%s" % path_info

        return file_path