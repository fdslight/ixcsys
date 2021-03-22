#!/usr/bin/env python3

import os


def __parse_proc_info_line(s: str):
    """解析单个进程行信息
    :param s:
    :return:
    """
    s = s.replace("\n", "")
    _list = s.split(" ")
    tmplist = []
    for x in _list:
        x = x.strip()
        if not x: continue
        tmplist.append(x)

    dic = {
        "UID": tmplist[0],
        "PID": tmplist[1],
        "PPID": tmplist[2],
        "C": tmplist[3],
        "STIME": tmplist[4],
        "TTY": tmplist[5],
        "TIME": tmplist[6],
        "CMD": " ".join(tmplist[7:])
    }
    return dic


def os_running_proc_get():
    """获取操作系统运行的进程
    :return:
    """
    fd = os.popen("ps -ef")
    results = []
    flags = False

    for line in fd:
        if not flags:
            flags = True
            continue
        proc_info = __parse_proc_info_line(line)
        results.append(proc_info)

    return results


def ixc_running_proc_get():
    """获取所有正在运行的IXC进程
    :return:
    """
    os_proc_list = os_running_proc_get()
    results = []
    for proc in os_proc_list:
        cmd = proc["CMD"]
        p = cmd.find("ixcsys")
        if p < 0: continue
        results.append(proc)

    return results
