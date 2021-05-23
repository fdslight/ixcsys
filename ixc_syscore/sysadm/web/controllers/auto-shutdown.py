#!/usr/bin/env python3

import os
import ixc_syscore.sysadm.web.controllers.controller as base_controller

import ixc_syslib.pylib.RPCClient as RPC


class controller(base_controller.BaseController):
    def myinit(self):
        self.request.set_allow_methods(["POST"])
        return True

    def handle(self):
        shutdown_type = self.request.get_argument("auto_shutdown_type", is_seq=False, is_qs=False)
        begin_hour = self.request.get_argument("beign_hour", is_seq=False, is_qs=False)
        begin_min = self.request.get_argument("beign_min", is_seq=False, is_qs=False)

        end_hour = self.request.get_argument("end_hour", is_seq=False, is_qs=False)
        end_min = self.request.get_argument("end_min", is_seq=False, is_qs=False)

        if shutdown_type not in ("auto", "network", "time",):
            self.json_resp(True, "错误的关机控制类型")
            return

        try:
            i_begin_hour = int(begin_hour)
            i_begin_min = int(begin_min)
            i_end_hour = int(end_hour)
            i_end_min = int(end_min)
        except ValueError:
            self.json_resp(True, "不允许的时间值")
            return

        if i_begin_hour < 0 or i_begin_min < 0 or i_end_hour < 0 or i_end_min < 0:
            self.json_resp(True, "不允许的时间值")
            return

        if i_begin_hour > 23 or i_end_hour > 23:
            self.json_resp(True, "不允许的小时时间值")
            return

        if i_begin_min > 59 or i_end_min > 59:
            self.json_resp(True, "不允许的分钟时间值")
            return

        day_begin_seconds = i_begin_hour * 3600 + i_begin_min * 60
        day_end_seconds = i_end_hour * 3600 + i_end_min * 60

        if day_end_seconds - day_begin_seconds < 3600:
            self.json_resp(True, "结束时间必须大于开始时间,并且间隔不少于1小时")
            return


        self.json_resp(False, {})
