#!/usr/bin/env python3
import ixc_syslib.web.ui_widget as ui_widget
import ixc_syslib.pylib.RPCClient as RPC

from pywind.global_vars import global_vars


class widget(ui_widget.widget):
    def get_traffic_descr(self, size):
        """获取流量描述
        """
        seq = (
            "KB", "MB", "GB", "TB",
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

    def handle(self, *args, **kwargs):
        logs = {}
        traffic_info = global_vars["ixcsys.sysadm"].traffic_log_get()

        for hwaddr, info in traffic_info.items():
            logs[hwaddr] = {
                "ip4_addr": info["ip4_addr"],
                "ip6_addr": info["ip6_addr"],
                "rx_speed": self.get_traffic_descr(info["rx_speed"]),
                "tx_speed": self.get_traffic_descr(info["tx_speed"]),
                "rx_traffic": self.get_traffic_descr(info["rx_traffic"]),
                "tx_traffic": self.get_traffic_descr(info["tx_traffic"]),
                # 主机名
                "host_name": "-",
                # 厂商
                "vendor": "-",
                # 厂商LOGO
                "vendor_logo": "-"
            }
        return True, "traffic-log.html", logs
