#!/usr/bin/env python3
import json
import ixc_syscore.sysadm.web.controllers.controller as base_controller

import ixc_syslib.pylib.RPCClient as RPC


class controller(base_controller.BaseController):
    def myinit(self):
        self.request.set_allow_methods(["POST"])
        return True

    def handle_post(self):
        self.finish_with_json({})

    def get_info(self):
        """获取信息
        :return:
        """
        fpath = "%s/wake_on_lan.json" % self.my_config_dir
        with open(fpath, "r") as f: s = f.read()
        f.close()

        return json.loads(s)

    def save(self, dic: dict):
        fpath = "%s/wake_on_lan.json" % self.my_config_dir
        with open(fpath, "w") as f: f.write(json.dumps(dic))
        f.close()

    def add(self, alias_name: str, hwaddr: str):
        """增加硬件地址
        :param alias_name:
        :param hwaddr:
        :return:
        """
        info = self.get_info()

        if alias_name in info: return

        info[alias_name] = hwaddr
        self.save(info)

    def delete(self, alias_name: str):
        """
        :param alias_name:
        :return:
        """
        info = self.get_info()
        if alias_name not in info: return
        del info[alias_name]
        self.save(info)

    def handle(self):
        action = self.request.get_argument("action", is_seq=False, is_qs=True)
        hwaddr = self.request.get_argument("hwaddr", is_seq=False, is_qs=False)
        alias_name = self.request.get_argument("alias_name", is_seq=False, is_qs=False)

        if action not in ("add", "delete",):
            self.json_resp(True, "错误的请求动作")
            return

        # 此处检查硬件地址是否合法

        self.json_resp(False, {})
