#!/usr/bin/env python3
"""能源监控类
"""
import os
import time, socket
import pywind.lib.netutils as netutils
import ixc_syscore.sysadm.pylib.wol as wol


def shutdown(bind_ip, port):
    data = bytes([0xff]) * 128

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind((bind_ip, 0))
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    s.sendto(data, ("255.255.255.255", port))
    s.close()


class power_monitor(object):
    __hwaddrs = None
    __up_time = None
    __day_begin_time = None
    __day_end_time = None

    __shutdown_type = None
    __check_network_count = None

    __bind_ip = None
    __port = None

    __https_host = None
    __enabled = None

    __self_shutdown_time = None
    __network_error_time = None

    def __init__(self, begin_hour: int, begin_min: int, end_hour: int, end_min: int, https_host: str, bind_ip: str,
                 port: int,
                 shutdown_type: str):
        self.__hwaddrs = []
        self.__up_time = time.time()
        self.set_time(begin_hour, begin_min, end_hour, end_min)
        self.__check_network_count = 0

        self.__https_host = https_host
        self.__bind_ip = bind_ip
        self.__port = port
        self.__shutdown_type = shutdown_type
        self.__enabled = False
        self.__self_shutdown_time = 0
        self.__network_error_time = 0

    def set_time(self, begin_hour: int, begin_min: int, end_hour: int, end_min: int):
        self.__day_begin_time = begin_hour * 60 + begin_min
        self.__day_end_time = end_hour * 60 + end_min

    def set_https_host(self, host: str):
        self.__https_host = host

    def set_shutdown_type(self, _type):
        self.__shutdown_type = _type

    def set_self_shutdown_time(self, minute: int):
        self.__self_shutdown_time = minute

    def get_day_min(self):
        """获取一天的分钟数目
        """
        hour = time.strftime("%H")
        minute = time.strftime("%M")

        return int(hour) * 60 + int(minute)

    def add_hwaddr(self, hwaddr: str):
        if hwaddr not in self.__hwaddrs: self.__hwaddrs.append(hwaddr)

    def clear(self):
        self.__hwaddrs = []
        self.__check_network_count = 0

    def check_network_ok(self):
        """检查网络是否成功
        """
        is_ipv6_addr = netutils.is_ipv6_address(self.__https_host)

        if is_ipv6_addr:
            fa = socket.AF_INET6
        else:
            fa = socket.AF_INET

        s = socket.socket(fa, socket.SOCK_STREAM)
        s.settimeout(3)

        # 超过3次都是失败那么返回网络失败
        try:
            s.connect((self.__https_host, 443))
            self.__check_network_count = 0
        except:
            self.__check_network_count += 1
            self.__network_error_time = self.get_day_min()

        if self.__check_network_count >= 3:
            return False

        return True

    def power_off(self):
        """关闭电源
        """
        shutdown(self.__bind_ip, self.__port)

    def power_on(self):
        """打开电源
        """
        for hwaddr in self.__hwaddrs:
            instance = wol.wake_on_lan()
            instance.wake(hwaddr)

    def is_need_power_off(self):
        day_min = self.get_day_min()

        if self.__shutdown_type in ("auto", "time",):
            if day_min < self.__day_begin_time or day_min > self.__day_end_time: return True

        if self.__shutdown_type in ("auto", "network",):
            network_ok = self.check_network_ok()
            if not network_ok: return True

        return False

    def is_need_power_on(self):
        day_min = self.get_day_min()

        if self.__shutdown_type in ("auto", "time",):
            if day_min >= self.__day_begin_time or day_min <= self.__day_end_time: return True

        if self.__shutdown_type in ("auto", "network",):
            network_ok = self.check_network_ok()
            if not network_ok: return True

        return False

    def is_need_self_shutdown(self):
        if self.__check_network_count == 0:
            return False
        if self.__self_shutdown_time == 0:
            return False

        now_min = self.get_day_min()
        if now_min - self.__network_error_time > self.__self_shutdown_time: return True

        return False

    def set_enable(self, enabled: bool):
        """开启或者关闭能源管理
        """
        self.__enabled = enabled

    def loop(self):
        """循环跳用
        """
        if not self.__enabled: return
        now = time.time()
        # 60s执行一次
        if now - self.__up_time < 90: return

        is_sent_power_on = False

        if self.is_need_power_on():
            self.power_on()
            is_sent_power_on = True
        # 避免发送开机又发送关机
        if self.is_need_power_off() and not is_sent_power_on:
            self.power_off()

        # 如果需要自动关机,那么自动关机
        if self.is_need_self_shutdown():
            os.system("halt -p")

        self.__up_time = now
