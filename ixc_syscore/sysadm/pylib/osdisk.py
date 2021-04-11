#!/usr/bin/env python3
# 操作系统磁盘相关库
import os


def get_os_disks():
    """获取系统所有磁盘
    """
    fdst = os.popen("fdisk -l")
