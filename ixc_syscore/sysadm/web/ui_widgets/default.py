#!/usr/bin/env python3
import platform, os, sys
import time

import ixc_syslib.web.ui_widget as ui_widget
import ixc_syslib.pylib.RPCClient as RPC
import ixc_syslib.pylib.os_info as os_info

from pywind.global_vars import global_vars


class widget(ui_widget.widget):
    @property
    def sysadm(self):
        return global_vars["ixcsys.sysadm"]

    def have_update(self):
        """检查更新是否存在
        """
        fpath = "/tmp/ixcsys_update.tar.gz"
        return os.path.isfile(fpath)

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
        if platform.machine().lower() == "x86_64":
            fdst = os.popen("""cat /proc/cpuinfo | grep "model name" | sed -n "1p" | cut -b 14-""")
            cpu_model = fdst.read()
            fdst.close()

            return cpu_model.replace("\n", "")

        import ixc_syslib.pylib.armcpu as armcpu
        inst = armcpu.armcpu_info()
        cpus_info = inst.cpu_info_get()

        results = {}

        for vendor_name in cpus_info:
            if vendor_name not in results:
                results[vendor_name] = {}
            dic = results[vendor_name]
            for o in cpus_info[vendor_name]:
                if o["part_name"] not in dic:
                    dic[o["part_name"]] = 0
                dic[o["part_name"]] += 1

        _list = []
        for vendor_name in results:
            _list.append(vendor_name)
            dic = results[vendor_name]
            for part_name in dic:
                _list.append(part_name)
                _list.append("x%s" % dic[part_name])
                _list.append(",")
            ''''''
        return " ".join(_list[0:-1])

    def get_host_available_mem(self):
        """获取主机可用内存
        """
        cmd = "free -m | awk 'NR==2' | awk '{print $7}'"
        with os.popen(cmd) as f: mem = f.read()
        f.close()

        return mem.replace("\n", "")

    def get_traffic_size_descr(self, size):
        """获取流量大小描述
        """
        seq = (
            "KB", "MB", "GB", "TB", "PB", "EB",
        )
        s = ""
        idx = 0
        seq_len = len(seq)
        while 1:
            if idx >= seq_len: break
            size = size / 1000
            s = "%.3f %s" % (size, seq[idx])
            if size < 1000: break
            idx += 1

        return s

    def get_format_run_time(self):
        now_time = time.time()
        start_time = RPC.fn_call("router", "/config", "router_start_time")
        v = now_time - start_time

        tot_days = int(v / 86400)
        tot_hours = int(v / 3600)
        tot_minutes = int(v / 60)

        # 运行天数
        run_days = tot_days
        # 运行小时数目
        run_hours = int((v - tot_days * 86400) / 3600)
        # 运行分钟数目
        run_minutes = int((v - tot_hours * 3600) / 60)
        # 运行秒数
        run_secs = int(v - tot_minutes * 60)

        return {
            "run_days": run_days,
            "run_hours": run_hours,
            "run_minutes": run_minutes,
            "run_seconds": run_secs,
        }

    def handle(self, *args, **kwargs):
        uri = "default.html"
        dic = {}

        dic["time"] = time.strftime("%Y-%m-%d %H:%M:%S %Z")
        dic["have_update"] = self.have_update()

        rx_traffic_size, tx_traffic_size = RPC.fn_call("router", "/config", "wan_traffic_get")

        rx_traffic_descr = self.get_traffic_size_descr(rx_traffic_size)
        tx_traffic_descr = self.get_traffic_size_descr(tx_traffic_size)

        dic["rx_traffic"] = rx_traffic_descr
        dic["tx_traffic"] = tx_traffic_descr

        rx_traffic_speed, tx_traffic_speed, rx_npkt_speed, tx_npkt_speed = RPC.fn_call("router", "/config",
                                                                                       "wan_traffic_speed_get")

        # 按照Bit方式显示速度
        rx_speed_descr = self.get_traffic_size_descr(rx_traffic_speed * 8)
        tx_speed_descr = self.get_traffic_size_descr(tx_traffic_speed * 8)

        dic["rx_traffic_speed"] = rx_speed_descr.replace("B", "b") + "it"
        dic["tx_traffic_speed"] = tx_speed_descr.replace("B", "b") + "it"

        dic["rx_npkt_speed"] = rx_npkt_speed
        dic["tx_npkt_speed"] = tx_npkt_speed

        dic["start_time"] = self.get_format_run_time()

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
        dic["host_os"] = os_info.get_os_info()[0]

        return True, uri, dic
