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
        clients = RPC.fn_call("DHCP", "/dhcp_server", "get_clients")
        print(clients)
        # 此处转换bytes host_name编码
        for dic in clients:
            host_name = dic["host_name"]
            if not host_name:
                host_name = "-"
            else:
                host_name = host_name.decode("iso-8859-1")
            dic["host_name"] = host_name

        dhcp_kv = {}
        for o in clients:
            hwaddr = o["hwaddr"]
            dhcp_kv[hwaddr] = o

        ieee_mac_alloc_info = RPC.fn_call("DHCP", "/dhcp_server", "ieee_mac_alloc_info_get")

        logs = {}
        traffic_info = global_vars["ixcsys.sysadm"].traffic_log_get()
        print(traffic_info)
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
                "vendor": "",
            }
            # 从DHCP记录中获取主机名
            if hwaddr in dhcp_kv:
                logs[hwaddr]["host_name"] = dhcp_kv[hwaddr]["host_name"]

            # 查找MAC地址所属厂商
            t = hwaddr.replace(":", "")
            k = t[0:6].upper()
            vendor = ieee_mac_alloc_info.get(k, "unkown")
            logs[hwaddr]["vendor"] = vendor

        return True, "traffic-log.html", {"logs": logs}
