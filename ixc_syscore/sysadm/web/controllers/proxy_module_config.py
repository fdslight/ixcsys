#!/usr/bin/env python3
import json

import ixc_syscore.sysadm.web.controllers.controller as base_controller

import ixc_syslib.pylib.RPCClient as RPC


class controller(base_controller.BaseController):
    def myinit(self):
        self.request.set_allow_methods(["GET", "POST"])
        return True

    def handle_post(self):
        name = self.request.get_argument("module", is_seq=False, is_qs=False)
        conf = self.request.get_argument("conf", is_seq=False, is_qs=False)

        try:
            o = json.loads(conf)
        except:
            self.finish_with_json({"is_error": True, "message": "错误配置文件内容格式,配置文件必须为JSON映射格式"})
            return

        if not isinstance(o, dict):
            self.finish_with_json({"is_error": True, "message": "错误配置文件内容格式,配置文件必须为JSON映射格式"})
            return

        rs = RPC.fn_call("proxy", "/config", "update_crypto_module_conf", name, o)
        if not rs:
            self.finish_with_json({"is_error": True, "message": "更新加密模块配置失败"})
            return

        self.finish_with_json({"is_error": False, "message": "更新加密模块成功"})

    def handle_get(self):
        name = self.request.get_argument("module", is_seq=False, is_qs=True)
        conf = RPC.fn_call("proxy", "/config", "get_crypto_module_conf", name)
        if conf == None:
            is_error = True
            msg = "没有找到加密模块%s" % name
        else:
            is_error = False
            msg = conf
        self.finish_with_json({"is_error": is_error, "message": msg})

    def handle(self):
        if self.request.environ["REQUEST_METHOD"].upper() == "GET":
            self.handle_get()
            return
        self.handle_post()
