#!/usr/bin/env python3
import socket, time
import pywind.lib.netutils as netutils


def ipaddr_plus_plus(byte_addr: bytes):
    """对IP地址进行++操作
    """
    _list = list(byte_addr)
    _list.reverse()
    _list_new = []

    overflow = 0
    is_first = True
    for i in _list:
        if not is_first and overflow < 1:
            _list_new.append(i)
            continue
        if is_first:
            x = i + 1
            if x > 0xff:
                x = 0
                overflow = 1
            is_first = False
        else:
            x = i + overflow
            if x > 0xff:
                x = 0
            else:
                overflow = 0

        _list_new.append(x)

    _list_new.reverse()

    return bytes(_list_new)


class alloc(object):
    __empty_ipaddrs = None

    # IP 地址与MAC地址的绑定
    __bind = None

    __begin_addr = None
    __end_addr = None

    # 当前地址
    __cur_byte_addr = None

    # 不可用的地址映射记录
    __unable_addr_map = None

    __prefix = None
    __is_ipv6 = None
    __subnet = None

    def __init__(self, addr_begin: str, addr_end: str, subnet: str, prefix: int, is_ipv6=False):
        self.__bind = {}
        self.__empty_ipaddrs = []

        if is_ipv6:
            fa = socket.AF_INET6
        else:
            fa = socket.AF_INET

        self.__begin_addr = socket.inet_pton(fa, addr_begin)
        self.__end_addr = socket.inet_pton(fa, addr_end)
        self.__cur_byte_addr = self.__begin_addr
        self.__unable_addr_map = {}
        self.__prefix = prefix
        self.__is_ipv6 = is_ipv6
        self.__subnet = subnet

    def bind_ipaddr(self, hwaddr: str, ipaddr: str, timeout: int):
        """绑定IP地址
        :param hwaddr,硬件地址
        :param ipaddr,IP地址
        :param timeout,如果超时小于等于0,那么该IP地址那么永久不失效
        """
        self.__bind[hwaddr] = {
            "time": 0,
            "ip": ipaddr,
        }
        if timeout > 0: self.__bind[hwaddr]["time"] = time.time() + timeout
        self.__unable_addr_map[ipaddr] = None

    def unbind_ipaddr(self, hwaddr: str):
        if hwaddr in self.__bind: del self.__bind[hwaddr]

    def set_ip_status(self, hwaddr: str, avaliable: bool):
        """设置IP地址状态
        """
        if not avaliable:
            self.__unable_addr_map[hwaddr] = None
            return
        if hwaddr in self.__unable_addr_map: del self.__unable_addr_map[hwaddr]

    def get_ipaddr(self, hwaddr: str):
        if hwaddr:
            if hwaddr in self.__bind: return self.__bind[hwaddr]["ip"]
        if self.__is_ipv6:
            fa = socket.AF_INET6
        else:
            fa = socket.AF_INET

        if self.__empty_ipaddrs:
            byte_addr = self.__empty_ipaddrs.pop(0)
            return byte_addr

        rs_addr = None
        while 1:
            if self.__cur_byte_addr == self.__end_addr: return None
            addr = socket.inet_ntop(fa, self.__cur_byte_addr)
            if addr in self.__unable_addr_map:
                byte_addr = ipaddr_plus_plus(self.__cur_byte_addr)
                self.__cur_byte_addr = byte_addr
                continue
            rs_addr = self.__cur_byte_addr
            byte_addr = ipaddr_plus_plus(self.__cur_byte_addr)
            self.__cur_byte_addr = byte_addr
            break

        addr = socket.inet_ntop(fa, rs_addr)
        rs = netutils.is_subnet(addr, self.__prefix, self.__subnet)
        if not rs:
            self.__cur_byte_addr = self.__end_addr
            return None
        return addr

    def recycle(self):
        """回收IP地址
        """
        now = time.time()
        dels = []
        for hwaddr in self.__bind:
            o = self.__bind[hwaddr]
            if o["time"] - now <= 0: dels.append(hwaddr)
        for hwaddr in dels:
            ipaddr = self.__bind[hwaddr]
            del self.__unable_addr_map[ipaddr]
            del self.__bind[hwaddr]


"""
cls = alloc("192.168.1.8", "192.168.1.128", "192.168.1.0", 24)
cls.bind_ipaddr("xxxxx", "192.168.1.127", 100)
for x in range(129):
    rs = cls.get_ipaddr("xxxxx")
    if not rs: continue
    print(rs)
"""
