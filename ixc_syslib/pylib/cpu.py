#!/usr/bin/env python3
import os


def get_cpu_temperature():
    """获取CPU温度,因为所有CPU温度差不多,获取0号CPU即可
    """
    try_files = [
        "/sys/class/hwmon/hwmon0/temp1_input",
        "/sys/class/thermal/thermal_zone0/temp",
        "/sys/devices/virtual/thermal/thermal_thermal0/zone0/temp"
    ]

    temp = None

    for file in try_files:
        if not os.path.isfile(file): continue
        with open(file, "r") as f:
            s = f.read()
        f.close()

        temp = int(s)

    return temp / 1000


temperature = get_cpu_temperature()
print(temperature)
