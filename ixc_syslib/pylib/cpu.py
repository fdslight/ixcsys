#!/usr/bin/env python3
import os


def get_cpu_temperature(cpu_seq: int):
    """获取CPU温度
    param cpu_seq:cpu序号
    """
    if cpu_seq < 0: return None

    try_files = [
        "/sys/class/hwmon/hwmon%s/temp1_input" % cpu_seq,
        "/sys/class/thermal/thermal_zone%s/temp" % cpu_seq,
        "/sys/devices/virtual/thermal/thermal_zone%s/temp" % cpu_seq
    ]

    temp = None

    for file in try_files:
        if not os.path.isfile(file): continue
        with open(file, "r") as f:
            s = f.read()
        f.close()

        temp = int(s)

    if temp is None: return temp

    return round(temp / 1000, 2)


def get_cpu_cur_freq(cpu_seq: int):
    if cpu_seq < 0: return -1

    cpu_cur_freq = -1

    try_files = [
        "/sys/devices/system/cpu/cpu%s/cpufreq/cpuinfo_cur_freq" % cpu_seq,
        "/sys/devices/system/cpu/cpu%s/cpufreq/scaling_cur_freq" % cpu_seq,
    ]

    for file in try_files:
        if not os.path.isfile(file): continue
        with open(file, "r") as f:
            s = f.read()
        f.close()
        cpu_cur_freq = round(int(s) / 1000, 2)

    return cpu_cur_freq
