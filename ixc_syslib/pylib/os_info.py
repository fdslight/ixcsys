#!/usr/bin/env python3

import subprocess


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
    rs = subprocess.run("lsb_release -i", capture_output=True, shell=True)
    s = rs.stdout.decode()
    dis_id = __get_os_info_for_line(s)

    rs = subprocess.run("lsb_release -r", capture_output=True, shell=True)
    s = rs.stdout.decode()

    release = __get_os_info_for_line(s)

    rs = subprocess.run("lsb_release -d", capture_output=True, shell=True)
    s = rs.stdout.decode()

    dis = __get_os_info_for_line(s)

    return dis, dis_id, release
