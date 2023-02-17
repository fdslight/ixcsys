#!/usr/bin/env python3
import os


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
