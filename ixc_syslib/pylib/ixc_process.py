#!/usr/bin/env python3
import os,time


def get_process():
    results = []
    fdst = os.popen("ps aux | grep ixc_syscore")

    for line in fdst:
        _list = []
        line = line.replace("\n", "")
        line = line.replace("\r", "")
        tmplist = line.split(" ")
        for s in tmplist:
            if not s: continue
            _list.append(s)
        m = {
            "USER": _list[0],
            "PID": _list[1],
            "CPU_prt": _list[2],
            "mem_prt": _list[3],
            "VSZ": _list[4],
            "RSS": _list[5],
            "TTY": _list[6],
            "START": _list[7],
            "TIME": " ".join(_list[8:10]),
            "COMMAND": " ".join(_list[10:])
        }
        if m["COMMAND"].find("grep") >= 0: continue
        results.append(m)

    fdst.close()
    return results


def get_cpu_stat():
    """获取CPU状态
    """
    fdst = os.popen("cat /proc/stat | grep cpu")
    results = []

    for line in fdst:
        line = line.replace("\r", "")
        line = line.replace("\n", "")
        _tmplist = line.split(" ")
        _list = []

        for s in _tmplist:
            s = s.strip()
            if not s: continue
            _list.append(s)

        o = {
            "user": int(_list[1]),
            "nice": int(_list[2]),
            "system": int(_list[3]),
            "idle": int(_list[4]),
            "iowait": int(_list[5]),
            "irq": int(_list[6]),
            "softirq": int(_list[7]),
        }

        results.append((_list[0], o))

    fdst.close()

    return results


def get_cpu_time():
    """获取CPU时间
    """
    results = []
    stat = get_cpu_stat()
    for cpu_index, o in stat:
        a = o["user"] + o["nice"] + o["system"] + o["idle"] + o["iowait"] + o["irq"] + o["softirq"]
        results.append((cpu_index, a, o["idle"],))

    return results


def get_cpu_usage():
    """获取CPU使用率
    """
    begin_list = get_cpu_time()
    time.sleep(1)
    end_list = get_cpu_time()
    count = 0
    results = []
    for cpu_idx, e, idle_e in end_list:
        b = begin_list[count][1]
        tot_time = e - b
        idle_b = begin_list[count][2]

        idle = idle_e - idle_b
        usage = 1 - idle / tot_time
        results.append((cpu_idx, usage,))
        count += 1

    return results