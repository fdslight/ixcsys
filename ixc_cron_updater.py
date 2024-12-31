#!/usr/bin/env python3
# 自动更新路由器软件脚本
import os, sys, time, hashlib, json, platform

sys_dir = os.path.dirname(os.path.abspath(__file__))

sys.path.append(sys_dir)

# 更新文件路径
UPDATE_FILE = "/tmp/ixcsys_update.tar.gz"


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


def is_stopped_all_process():
    """检查所有进程是否都已经停止
    """
    results = []
    fdst = os.popen("ps -ef | grep ixc_")

    for line in fdst:
        _list = []
        line = line.replace("\n", "")
        line = line.replace("\r", "")
        # 去除非ixcsys进程
        if line.find("tftpd") >= 0: continue
        if line.find("grep") >= 0: continue
        if line.find("cron_updater") >= 0: continue
        results.append(line)

    # print(results)
    if not results: return True
    return False


def check_os_env(fpath: str):
    """检查操作系统环境
    """
    if not os.path.isfile(fpath): return False

    with open(fpath, "r") as f:
        s = f.read()
    f.close()

    o = json.loads(s)

    dis, dis_id, release = get_os_info()

    if o["distributor_id"] != dis_id.lower(): return False
    if o["release"] != release.lower(): return False
    if o["arch"] != platform.machine().lower(): return False

    return True


def update_router_file():
    """更新路由系统文件
    """
    d = "/tmp/ixcsys_update"
    update_check_file = "/tmp/ixcsys_update_check.md5"

    if not os.path.isdir(d): os.mkdir(d)

    # MD5校验文件不存在那么禁止更新
    if not os.path.isfile(update_check_file):
        print("UPDATE ERROR:not found update_check_file")
        return

    fdst = open(update_check_file, "rb")
    file_md5 = fdst.read()
    fdst.close()

    md5 = hashlib.md5()
    fdst = open(UPDATE_FILE, "rb")
    while 1:
        read = fdst.read(8192)
        if not read: break
        md5.update(read)
    fdst.close()

    if md5.digest() != file_md5:
        print("UPDATE ERROR:wrong update file md5")
        return

    os.system("tar xf %s -C %s" % (UPDATE_FILE, d))
    os.chdir(d)

    if not check_os_env("host_info"):
        print("Wrong host environment")
        return

    _list = os.listdir(".")

    for x in _list:
        if x == "ixc_configs":
            os.system("cp -r -n ixc_configs %s" % sys_dir)
            continue
        if x == "net_monitor.ini":
            os.system("cp -n net_monitor.ini %s" % sys_dir)
            continue
        os.system("cp -r %s %s" % (x, sys_dir))
        """"""
    os.system("rm -rf ./*")
    os.remove(UPDATE_FILE)


def do_update():
    if not os.path.isfile(UPDATE_FILE): return

    cmd = "%s /opt/ixcsys/ixc_main.py stop" % sys.executable
    os.system(cmd)

    while 1:
        time.sleep(30)
        if is_stopped_all_process():
            update_router_file()
            break
        ''''''
    cmd = "%s /opt/ixcsys/ixc_main.py service_start" % sys.executable
    os.system(cmd)


def do_update_immediately():
    pid = os.fork()
    if pid != 0: sys.exit(0)

    os.setsid()
    os.umask(0)
    pid = os.fork()

    if pid != 0: sys.exit(0)
    do_update()


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
            # print("NOTIFY:start auto update  %s" % time.strftime("%Y-%m-%d %H:%M:%S"))
            do_update()

        time.sleep(30)


def main():
    helper = """argument   HOUR:MINUTE or immediately"""
    user = os.getenv("USER")
    if user.lower() != "root":
        print("ERROR:run this script must be root user")
        return

    if len(sys.argv) != 2:
        print(helper)
        return

    if sys.argv[1] == "immediately":
        do_update_immediately()
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
