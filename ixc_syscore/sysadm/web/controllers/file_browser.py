#!/usr/bin/env python3

import os, time

from pywind.global_vars import global_vars

import ixc_syscore.sysadm.web.controllers.controller as base_controller


class controller(base_controller.BaseController):
    __file_object = None

    @property
    def sysadm(self):
        return global_vars["ixcsys.sysadm"]

    @property
    def enable_download(self):
        cfg = self.sysadm.download_cfg
        return bool(int(cfg["enable"]))

    @property
    def download_dir(self):
        cfg = self.sysadm.download_cfg
        return cfg["dir"]

    def myinit(self):
        self.request.set_allow_methods(["GET"])
        self.set_auto_auth(False)
        self.__file_object = None

        return True

    def start_send_file(self, path: str):
        if not os.path.isfile(path):
            self.set_status("403 Forbidden")
            self.finish()
            return
        try:
            self.__file_object = open(path, "rb")
        except:
            self.set_status("403 Forbidden")
            self.finish()
            return
        st = os.stat(path)
        self.set_status("200 OK")
        self.set_header("Content-Type", "application/octet-stream")
        self.set_header("Content-Length", st.st_size)

    def async_send_file(self):
        rdata = self.__file_object.read(4096)
        if not rdata:
            self.__file_object.close()
            self.__file_object = None
            self.finish()
            return
        self.write(rdata)

    def handle(self):
        if not self.enable_download:
            self.set_status("403 Forbidden")
            self.finish()
            return

        if self.__file_object:
            self.async_send_file()
            return

        root_dir = self.download_dir
        path_info = self.request.environ["PATH_INFO"]
        results = []

        path_info = path_info[1:]
        if root_dir[-1] == "/":
            d = "%s%s" % (root_dir, path_info)
        else:
            d = "%s/%s" % (root_dir, path_info,)

        if not os.path.isdir(d):
            self.start_send_file(d)
            return

        _list = os.listdir(d)

        if not path_info:
            file_path = "%s/files" % self.url_prefix
        else:
            tmplist = path_info.split("/")
            tmplist.pop()
            t = "/".join(tmplist)
            file_path = "%s/files/%s" % (self.url_prefix, t,)

        # 首先加入一个指向上一个目录的链接
        results.append(
            {
                "type": "-",
                "size": "-",
                "name": "..",
                "path": file_path,
                "mtime": "-",
                "ctime": "-"
            }
        )

        for x in _list:
            if d[-1] == "/":
                path = "%s%s" % (d, x)
            else:
                path = "%s/%s" % (d, x,)
            st = os.stat(path)
            mtime = st.st_mtime
            ctime = st.st_ctime
            size = st.st_size
            text_size = size

            if os.path.isfile(path):
                _type = "file"
            elif os.path.isdir(path):
                _type = "directory"
            else:
                _type = "other"

            if path_info:
                file_path = "%s/files/%s/%s" % (self.url_prefix, path_info, x)
            else:
                file_path = "%s/files/%s" % (self.url_prefix, x,)

            o = {
                "type": _type,
                "size": text_size,
                "name": x,
                "path": file_path,
                "mtime": time.ctime(mtime),
                "ctime": time.ctime(ctime)
            }
            results.append(o)

        self.render("file-show.html", "text/html;charset=utf-8", files=results, cur_dir=path_info)

    def release(self):
        if self.__file_object: self.__file_object.close()
        self.__file_object = None
