#!/usr/bin/env python3

from pywind.global_vars import global_vars

import ixc_syslib.web.controllers.rpc_controller as rpc


class controller(rpc.controller):
    __runtime = None

    def rpc_init(self):
        self.__runtime = global_vars["ixcsys.init"]

        self.fobjs = {
            "syslog_info_get": self.syslog_info_get,
            "syslog_alert_get": self.syslog_alert_get,
            "errlog_get": self.errlog_get,
            "errlog_clear_immediately": self.errlog_clear_immediately,
        }

    def syslog_info_get(self):
        return 0, self.__runtime.get_info_syslog()

    def syslog_alert_get(self):
        return 0, self.__runtime.get_alert_syslog()

    def errlog_get(self):
        return 0, self.__runtime.get_errlog()

    def errlog_clear_immediately(self):
        """立即清除故障日志
        """
        return 0, self.__runtime.error_log_clear()
