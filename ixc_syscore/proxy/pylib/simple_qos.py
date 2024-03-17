#!/usr/bin/env python3

### QOS类型
# 根据源地址进行QOS
QTYPE_SRC = 1
# 根据目的地址进行QOS
QTYPE_DST = 2


class qos(object):
    __qos_queue = None
    __qtype = 0

    def __init__(self, qtype):
        self.__qos_queue = {}
        self.__qtype = qtype

    def add_to_queue(self, ipdata):
        ip_ver = (ipdata[0] & 0xf0) >> 4

        if ip_ver == 4:
            if self.__qtype == QTYPE_SRC:
                address = ipdata[12:16]
            else:
                address = ipdata[16:20]
        else:
            if self.__qtype == QTYPE_SRC:
                address = ipdata[8:24]
            else:
                address = ipdata[24:40]

        slot = address

        if slot not in self.__qos_queue:
            self.__qos_queue[slot] = []

        self.__qos_queue[slot].append(ipdata)

    def get_queue(self):
        """对流量进行重新排序
        :return: 
        """
        results = []
        dels = []

        for slot in self.__qos_queue:
            seq = self.__qos_queue[slot]
            results.append(seq.pop(0))
            if not seq: dels.append(slot)

        for slot in dels:
            del self.__qos_queue[slot]

        return results
