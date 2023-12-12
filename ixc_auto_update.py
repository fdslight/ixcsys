#!/usr/bin/env python3
# 自动更新程序脚本,该脚本不会通过ixc_main.py启动,只能人工启动或者设置操作系统开机自启动
# 注意,启动时候要与ixc_main.py为同一个Python3环境,即相同的启动命令

import os, time, struct, sys

sys_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(sys_dir)


class updater(object):
    # 计划更新配置文件路径
    __plan_update_cfg_path = None

    def __init__(self):
        self.__plan_update_cfg_path = "%s/auto_update.time" % sys_dir

    def update_file_exists(self):
        """检查更新文件是否存在"""
        fpath = "/tmp/ixcsys_update.tar.gz"

        return os.path.isfile(fpath)

    def read_update_time(self):
        if not os.path.isfile(self.__plan_update_cfg_path): return -1
        with open(self.__plan_update_cfg_path, "rb") as f:
            t = f.read()
        f.close()
        if len(t) != 4: return -1

        seconds, = struct.unpack("I", t)

        return seconds

    def do_update(self):
        h = time.strftime("%H")
        m = time.strftime("%M")

        now_h = int(h)
        now_m = int(m)

        now_seconds = now_h * 3600 + now_m * 60
        cron_seconds = self.read_update_time()

        if cron_seconds < 0: return

        # 时间未到不执行更新
        if now_seconds - cron_seconds < 0: return
        if not self.update_file_exists(): return

        # 执行更新动作
        cmd = "%s ixc_main.py restart" % sys.executable
        os.system(cmd)

    def wait_update(self):
        while 1:
            self.do_update()
            time.sleep(60)
        ''''''


def main():
    pid = os.fork()
    if pid != 0: sys.exit(0)

    os.setsid()
    os.umask(0)
    pid = os.fork()

    if pid != 0: sys.exit(0)

    cls = updater()
    cls.wait_update()


if __name__ == '__main__': main()
