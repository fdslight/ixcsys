#!/usr/bin/env python3

import json, sys, platform, psutil, os
import ixc_syslib.web.controllers.ui_controller as base


class BaseController(base.controller):
    @property
    def user_configs(self):
        conf_path = "%s/user.json" % self.my_config_dir

        with open(conf_path, "r") as f: s = f.read()
        f.close()

        return json.loads(s)

    def json_resp(self, is_error: bool, message):
        """响应ajax
        """
        self.finish_with_json({"is_error": is_error, "message": message})

    def get_system_info(self):
        sys_info = {
            "os_type": sys.platform,
            "arch": platform.machine(),
            "cpu_count": os.cpu_count(),
            "mem_tot_size": psutil.virtual_memory().total,
            "mem_free_size": psutil.virtual_memory().free,
            "ixcsys_version": "1.0.0-b1"
        }
        return sys_info

    def get_wan_info(self):
        return {}

    def get_lan_info(self):
        return {}

    def __widget_applist(self):
        applist = []
        s = self.get_tpl_render_result("applist.html", apps=applist)
        return s

    def __widget_page_content(self):
        page = self.request.get_argument("page", is_qs=True, is_seq=False)
        pages = [
            "wan-pppoe",
            "wan-dhcp",
            "wan-static-ip",
            "wan-port-map",
            "system-network-wan",
            "system-network-lan",
            "system-info"
        ]
        if page not in pages: return "not found request page"
        if page == "wan-pppoe":
            return self.get_tpl_render_result("wan.html")
        if page == "wan-dhcp":
            return self.get_tpl_render_result("wan.html")
        if page == "wan-static-ip":
            return self.get_tpl_render_result("wan.html")
        if page == "wan-port-map":
            return self.get_tpl_render_result("port-map.html")

        if page == "system-network-wan":
            return self.get_tpl_render_result("system-network.html", **self.get_wan_info())
        if page == "system-network-lan":
            return self.get_tpl_render_result("system-network.html", **self.get_lan_info())
        if page == "system-info":
            return self.get_tpl_render_result("system-info.html", **self.get_system_info())

    def widget_init(self):
        self.widget_add("applist", self.__widget_applist)
        self.widget_add("page-content", self.__widget_page_content)
