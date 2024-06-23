#!/usr/bin/env python3
# 自动更新路由器软件脚本，如需要,请添加到root用户的定时器脚本中
import os

# 更新文件路径
UPDATE_FILE = "/tmp/ixcsys/ixcsys_update.tar.gz"


def main():
    user=os.getenv("USER")
    if user.lower()!="root":
        print("ERROR:run this script must be root user")
        return
    if not os.path.isfile(UPDATE_FILE):
        return



if __name__ == '__main__': main()
