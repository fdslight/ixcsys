#!/usr/bin/env python3
"""获取ARM CPU信息
"""
import os


class armcpu_info(object):
    __BASE_DIR = None

    def __init__(self):
        self.__BASE_DIR = "/sys/devices/system/cpu"

    def get_cpu_midr(self):
        """获取CPU
        """
        base_dir = self.__BASE_DIR
        _list = os.listdir(base_dir)

        results = []
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

            z = int(s, 16)

            results.append((cpu_no, z,))

        return results

    def get_cpu_model(self, cpu_midr_list: list):
        for cpu_no, midr_reg in cpu_midr_list:
            vendor_id = (midr_reg & 0xff000000) >> 24
            variant = (midr_reg & 0xf00000) >> 16
            arch = (midr_reg & 0x0f0000) >> 16
            part_number = (midr_reg & 0xfff0) >> 4
            revision = midr_reg & 0x0f

            print(hex(midr_reg),hex(vendor_id),hex(variant),hex(arch),hex(part_number),hex(revision))

    def cpu_info_get(self):
        midr_list = self.get_cpu_midr()
        self.get_cpu_model(midr_list)


cls = armcpu_info()
cls.cpu_info_get()
