#!/usr/bin/env python3
import platform, os, sys
import ixc_syslib.web.ui_widget as ui_widget
import ixc_syslib.pylib.RPCClient as RPC

from pywind.global_vars import global_vars


class widget(ui_widget.widget):
    @property
    def sysadm(self):
        return global_vars["ixcsys.sysadm"]

    def read_version(self):
        fpath = "%s/version" % self.sys_dir
        if not os.path.isfile(fpath):
            return "unkown"

        with open(fpath, "r") as f: s = f.read()
        f.close()

        return s

    def get_host_mem_total(self):
        """获取主机内存大小
        """
        with os.popen("grep MemTotal /proc/meminfo | awk '{print $2 / 1024}'") as f: mem_total = f.read()
        f.close()
        return mem_total.replace("\n", "")

    def get_host_cpu_model(self):
        """获取主机CPU型号
        """
        fdst = os.popen("""cat /proc/cpuinfo | grep "model name" | sed -n "1p" | cut -b 14-""")
        cpu_model = fdst.read()
        fdst.close()

        return cpu_model.replace("\n", "")

    def get_host_available_mem(self):
        """获取主机可用内存
        """
        cmd = "free -m | grep Mem | awk '{print $7}'"
        with os.popen(cmd) as f: mem = f.read()
        f.close()

        return mem.replace("\n", "")

    def handle(self, *args, **kwargs):
        uri = "default.html"
        dic = {}

        wan_configs = RPC.fn_call("router", "/config", "wan_config_get")
        pub = wan_configs["public"]
        dic["internet_type"] = pub["internet_type"]

        # wan_ip_info = RPC.fn_call("router", "/runtime", "get_wan_ipaddr_info", is_ipv6=False)

        nameservers = RPC.fn_call("DNS", "/config", "get_nameservers", is_ipv6=False)
        nameservers6 = RPC.fn_call("DNS", "/config", "get_nameservers", is_ipv6=True)

        dic["nameservers"] = nameservers
        dic["nameservers6"] = nameservers6

        wan_ipinfo = RPC.fn_call("router", "/config", "get_wan_ipaddr_info", is_ipv6=False)

        if not wan_ipinfo:
            dic["wan_ip"] = ""
            dic["wan_prefix"] = ""
        else:
            dic["wan_ip"] = wan_ipinfo[0]
            dic["wan_prefix"] = wan_ipinfo[1]

        dic["cpu_arch"] = platform.machine()
        dic["cpu_count"] = os.cpu_count()
        dic["version"] = self.read_version()

        dic["cpu_model"] = self.get_host_cpu_model()
        dic["total_mem"] = self.get_host_mem_total()
        dic["available_mem"] = self.get_host_available_mem()
        dic["is_temp_network"] = self.sysadm.network_is_work_on_temp

        return True, uri, dic
