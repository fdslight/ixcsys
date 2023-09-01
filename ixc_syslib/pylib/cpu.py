#!/usr/bin/env python3
import os


def get_cpu_temperature(cpu_seq: int):
    """获取CPU温度,因为所有CPU温度差不多,获取0号CPU即可
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

    return round(temp / 1000, 2)
