#!/usr/bin/env python3
"""能源监控类
"""
import time, socket


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

    def __init__(self, begin_hour: int, begin_min: int, end_hour: int, end_min: int, bind_ip: str, port: int,
                 shutdown_type: str):
        self.__hwaddrs = {}
        self.__shutdown_type = shutdown_type
        self.__up_time = time.time()
        self.__day_begin_time = begin_hour * 60 + begin_min
        self.__day_end_time = end_hour * 60 + end_min
        self.__check_network_count = 0

        self.__bind_ip = bind_ip
        self.__port = port

    def set_shutdown_type(self, _type):
        self.__shutdown_type = _type

    def get_day_min(self):
        """获取一天的分钟数目
        """
        hour = time.strftime("%H")
        minute = time.strftime("%M")

        return int(hour) * 60 + int(minute)

    def add_hwaddr(self, hwaddr: str):
        pass

    def clear(self):
        self.__hwaddrs = {}
        self.__check_network_count = 0

    def check_network_ok(self):
        """检查网络是否成功
        """
        return True

    def power_off(self):
        """关闭电源
        """
        shutdown(self.__bind_ip, self.__port)

    def power_on(self):
        """打开电源
        """
        pass

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

    def loop(self):
        """循环跳用
        """
        now = time.time()
        # 60s执行一次
        if now - self.__up_time < 60: return

        is_sent_power_on = False

        if self.is_need_power_on():
            self.power_on()
            is_sent_power_on = True
        # 避免发送开机又发送关机
        if self.is_need_power_off() and not is_sent_power_on: self.power_off()

        self.__up_time = now
