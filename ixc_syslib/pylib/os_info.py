#!/usr/bin/env python3

import os


def __get_os_info_for_line(s: str):
    s = s.replace("\n", "")
    s = s.replace("\r", "")
    p = s.find(":")
    if p < 0: return ""
    p += 1
    s = s[p:]
    s = s.strip()

    return s


def get_os_info():
    with os.popen("lsb_release -i") as f: s = f.read()
    f.close()
    dis_id = __get_os_info_for_line(s)

    with os.popen("lsb_release -r") as f: s = f.read()
    f.close()

    release = __get_os_info_for_line(s)

    with os.popen("lsb_release -d") as f: s = f.read()
    f.close()

    dis = __get_os_info_for_line(s)

    return dis, dis_id, release
