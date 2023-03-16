#!/usr/bin/env python3

import struct, time, socket

import pywind.lib.netutils as netutils

FMT = "6sBB16sQQQ"


class parser(object):
    __traffic_info = None
    __day = None

    def __init__(self):
        self.__traffic_info = {}
        self.__day = time.strftime("%Y-%m-%d")

    def parse(self, message: bytes):
        try:
            byte_hwaddr, is_tcpip, is_ipv6, byte_host_addr, up_time, rx_traffic, tx_traffic = struct.unpack(FMT,
                                                                                                            message)
        except struct.error:
            return

        # 是否计算速度
        calc_speed_flag = True
        hwaddr = netutils.byte_hwaddr_to_str(byte_hwaddr)

        if hwaddr not in self.__traffic_info:
            self.__traffic_info[hwaddr] = {
                "ip4_addr": "-",
                "ip6_addr": "-",
                "up_time": up_time,
                "rx_traffic": 0,
                "tx_traffic": 0,
                "rx_traffic_old": 0,
                "tx_traffic_old": 0,
                "rx_speed": 0,
                "tx_speed": 0
            }
            calc_speed_flag = False
        machine_info = self.__traffic_info[hwaddr]

        machine_info["rx_traffic"] += rx_traffic
        machine_info["tx_traffic"] += tx_traffic

        if bool(is_tcpip):
            if (is_ipv6):
                address = socket.inet_ntop(socket.AF_INET6, byte_host_addr)
                machine_info["ip6_addr"] = address
            else:
                address = socket.inet_ntop(socket.AF_INET, byte_host_addr[0:4])
                machine_info["ip4_addr"] = address
            ''''''

        if not calc_speed_flag: return

        old_up_time = machine_info["up_time"]
        if up_time - old_up_time < 5: return

        machine_info["up_time"] = up_time

        rx_traffic_size = machine_info["rx_traffic"] - machine_info["rx_traffic_old"]
        tx_traffic_size = machine_info["tx_traffic"] - machine_info["tx_traffic_old"]

        rx_speed = int(rx_traffic_size / (up_time - old_up_time))
        tx_speed = int(tx_traffic_size / (up_time - old_up_time))

        machine_info["rx_speed"] = rx_speed
        machine_info["tx_speed"] = tx_speed

        machine_info["rx_traffic_old"] = machine_info["rx_traffic"]
        machine_info["tx_traffic_old"] = machine_info["tx_traffic"]

    def is_need_clear(self):
        """是否需要清除,一天重置一次
        """
        now_day = time.strftime("%Y-%m-%d")
        if now_day != self.__day:
            self.__day = now_day
            return True
        return False

    def task_loop(self):
        if self.is_need_clear():
            self.__traffic_info = {}
        ''''''

    def traffic_log_get(self):
        return self.__traffic_info
