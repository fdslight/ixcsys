#!/usr/bin/env python3
"""获取ARM CPU信息
"""
import os

CPU_VENDOR_ID_MAP = {
    0x41: "ARM",
    0x42: "Broadcom",
    0x43: "Cavium",
    0x44: "DigitalEquipment",
    0x48: "HiSilicon",
    0x49: "Infineon",
    0x4D: "Freescale",
    0x4E: "NVIDIA",
    0x50: "APM",
    0x51: "Qualcomm",
    0x56: "Marvell",
    0x69: "Intel",
    0xC0: "Ampere"
}

CPU_PART_NUMBER_MAP = {
    0xd03: "Cortex-A53",
    0xd05: "Cortex-A55",
    0xd07: "Cortex-A57",
    0xd46: "Cortex‑A510",

    0xd08: "Cortex-A72",
    0xd09: "Cortex-A73",
    0xd0a: "Cortex-A75",
    0xd0b: "Cortex-A76",
    0xd47: "Cortex-A710",
    0xd4b: "Cortex-A78C",
}


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
        results = {}
        for cpu_no, midr_reg in cpu_midr_list:
            vendor_id = (midr_reg & 0xff000000) >> 24
            variant = (midr_reg & 0xf00000) >> 16
            arch = (midr_reg & 0x0f0000) >> 16
            part_number = (midr_reg & 0xfff0) >> 4
            revision = midr_reg & 0x0f

            if vendor_id not in CPU_VENDOR_ID_MAP:
                vendor_name = "unkown"
            else:
                vendor_name = CPU_VENDOR_ID_MAP[vendor_id]

            if vendor_name not in results:
                results[vendor_name] = []

            if part_number not in CPU_PART_NUMBER_MAP:
                part_name = "unkown"
            else:
                part_name = CPU_PART_NUMBER_MAP[part_number]

            dic = {
                "vendor_id": vendor_id,
                "variant": variant,
                "arch": arch,
                "part_number": part_number,
                "revision": revision,
                "vendor_name": vendor_name,
                "part_name": part_name
            }
            results[vendor_name].append(dic)

        return results

    def cpu_info_get(self):
        midr_list = self.get_cpu_midr()
        return self.get_cpu_model(midr_list)
