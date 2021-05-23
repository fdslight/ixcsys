#!/usr/bin/env python3

from pywind.global_vars import global_vars

import pywind.lib.configfile as conf

import ixc_syscore.sysadm.pylib.wol as wol
import ixc_syscore.sysadm.web.controllers.controller as base_controller


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
        fpath = "%s/wake_on_lan.ini" % self.my_config_dir
        return conf.ini_parse_from_file(fpath)

    def save(self, dic: dict):
        fpath = "%s/wake_on_lan.ini" % self.my_config_dir
        conf.save_to_ini(dic, fpath)

    def add(self):
        """增加硬件地址
        :param alias_name:
        :param hwaddr:
        :return:
        """
        hwaddr = self.request.get_argument("hwaddr", is_seq=False, is_qs=False)
        name = self.request.get_argument("name", is_seq=False, is_qs=False)
        add_to_power_ctl = self.request.get_argument("add_to_power_ctl", is_seq=False, is_qs=False)

        info = self.get_info()

        if not add_to_power_ctl:
            add_to_power_ctl = 0
        else:
            add_to_power_ctl = 1

        if name in info:
            self.finish_with_json({"is_error": True, "message": "机器名已经存在"})
            return

        info[name] = {"hwaddr": hwaddr, "add_to_power_ctl": add_to_power_ctl}

        self.save(info)
        self.finish_with_json({"is_error": False, "message": "添加成功"})

    def delete(self):
        name = self.request.get_argument("name", is_seq=False, is_qs=False)
        if not name:
            self.finish_with_json({"is_error": True, "message": "空的机器名"})
            return

        info = self.get_info()
        if name not in info:
            self.finish_with_json({"is_error": True, "message": "未找到机器名"})
            return

        del info[name]
        self.save(info)
        self.finish_with_json({"is_error": False, "message": "删除成功"})

    def wake(self):
        """唤醒机器
        :param hwaddr:
        :return:
        """
        hwaddr = self.request.get_argument("hwaddr", is_seq=False, is_qs=False)
        if not hwaddr:
            self.finish_with_json({"is_error": True, "message": "空的机器硬件地址"})
            return

        g = global_vars["ixcsys.sysadm"]

        manage_addr = g.get_manage_addr()
        w = wol.wake_on_lan(bind_ip=manage_addr)
        w.wake(hwaddr)

        self.finish_with_json({"is_error": False, "message": "唤醒成功"})

    def handle(self):
        action = self.request.get_argument("action", is_seq=False, is_qs=False)

        if action not in ("add", "delete", "wake",):
            self.finish_with_json({"is_error": True, "message": "错误的请求动作"})
            return

        if action == "add":
            self.add()
            return

        if action == "delete":
            self.delete()
            return

        self.wake()
