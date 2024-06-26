#!/usr/bin/env python3
# 自动更新路由器软件脚本
import os, sys, time

# 更新文件路径
UPDATE_FILE = "/tmp/ixcsys_update.tar.gz"


def do_update():
    if not os.path.isfile(UPDATE_FILE):
        return

    cmd = "%s /opt/ixcsys/ixc_main.py restart" % sys.executable
    os.system(cmd)


def start(h, m):
    pid = os.fork()
    if pid != 0: sys.exit(0)

    os.setsid()
    os.umask(0)
    pid = os.fork()

    if pid != 0: sys.exit(0)

    while 1:
        now_h = int(time.strftime("%H"))
        now_m = int(time.strftime("%M"))

        if now_h == h and now_m == m:
            #print("NOTIFY:start auto update  %s" % time.strftime("%Y-%m-%d %H:%M:%S"))
            do_update()

        time.sleep(30)


def main():
    helper = """argument   HOUR:MINUTE"""
    user = os.getenv("USER")
    if user.lower() != "root":
        print("ERROR:run this script must be root user")
        return

    if len(sys.argv) != 2:
        print(helper)
        return

    _list = sys.argv[1].split(":")
    if len(_list) != 2:
        print("ERROR:wrong time format")
        return

    h = _list[0]
    m = _list[1]

    try:
        h = int(h)
        m = int(m)
    except ValueError:
        print("ERROR:wrong time format")
        return

    if h < 0 or h > 23:
        print("ERROR:wrong time hour value format")
        return

    if m < 0 or m > 59:
        print("ERROR:wrong time minute value format")
        return

    start(h, m)


if __name__ == '__main__': main()
