#!/usr/bin/env python3
"""获取ARM CPU信息
"""
import os


class armcpu_info(object):
    __BASE_DIR = None

    def __init__(self):
        self.__BASE_DIR = "/sys/devices/system/cpu"

    def get_cpu_dir(self):
        """获取CPU
        """
        base_dir = self.__BASE_DIR
        _list = os.listdir(base_dir)

        _dict = {}
        for x in _list:
            if x[0:3] != "cpu": continue
            path = "%s/%s" % (base_dir, x,)
            if not os.path.isdir(path): continue
            try:
                cpu_no = int(x[3:])
            except ValueError:
                continue
            midr_el1_path = "%s/%s/regs/identification/midr_el1" % (base_dir, x,)
            fdst = open(midr_el1_path, "r")
            s = fdst.read()
            fdst.close()
            s = s.replace("\n", "")
            s = s.replace("\r", "")

            z = int(s)

            _dict[cpu_no] = z

        print(_dict)

    def arm_cpu_get(self):
        pass

cls=armcpu_info()
cls.get_cpu_dir()
