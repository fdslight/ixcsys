#!/usr/bin/env python3
import json
import os, sys, signal, time, traceback, hashlib
import importlib
import platform

sys_dir = os.path.dirname(os.path.abspath(__file__))

sys.path.append(sys_dir)

import ixc_syslib.pylib.os_info as os_info

# 必须要启动的服务,依照优先级顺序
must_services = [
    "ixc_syscore/init",
    "ixc_syscore/router",
    "ixc_syscore/PASS",
    "ixc_syscore/DHCP",
    "ixc_syscore/DNS",
    "ixc_syscore/sysadm",
    "ixc_syscore/proxy",
]

# 必需的Python模块
must_py_modules = {
    "dnspython3": "dns.message",
    "cryptography": "cryptography",
    "cloudflare-ddns": "cloudflare_ddns"
}


def check_py_modules():
    no_modules = []
    for name in must_py_modules:
        try:
            importlib.import_module(must_py_modules[name])
        except ImportError:
            no_modules.append(name)
        ''''''

    if no_modules:
        print("ERROR:not found python modules %s" % ",".join(no_modules))
        return False

    exe_dir = os.path.dirname(sys.executable)
    if not exe_dir:
        exe_dir = "."
    s_tui_path = "%s/s-tui" % exe_dir
    if not os.path.isfile(s_tui_path):
        print("ERROR:not found s-tui")
        return False

    return True


def set_pub_env():
    conf_dir = "%s/ixc_configs" % sys_dir
    sys_py_interpreter = sys.executable

    os.putenv("IXC_SYS_DIR", sys_dir)
    os.putenv("IXC_CONF_DIR", conf_dir)
    os.putenv("IXC_PYTHON", sys_py_interpreter)
    os.putenv("IXC_SYSROOT", sys_dir)

    if not os.path.isdir("/tmp/ixcsys"): os.mkdir("/tmp/ixcsys")


def start_all():
    for x in must_services:
        time.sleep(5)
        start(x, debug=False)


def stop_all():
    _list = must_services.copy()
    _list.reverse()
    for x in _list: stop(x)


def force_stop_router():
    """强制停止路由进程
    """
    path = "/tmp/ixcsys/router"
    stop("ixc_syscore/router")
    spath = "%s/rpc.sock" % path

    if os.path.exists(spath): os.remove(spath)

    # 清除未删除的设备
    del_devices = [
        "ixclan", "ixcwan", "ixclanbr", "ixcwanbr",
    ]
    for device in del_devices:
        fdst = os.popen("ip addr | grep %s" % device)
        s = fdst.read()
        s = s.replace("\n", "")
        fdst.close()
        if not s: continue
        os.system("ip link del %s" % device)


def start(uri: str, debug=False):
    if not debug:
        start_file = "sh %s/%s/start.sh" % (sys_dir, uri)
    else:
        start_file = "sh %s/%s/debug.sh" % (sys_dir, uri)
    os.putenv("IXC_MYAPP_DIR", "%s/%s" % (sys_dir, uri))

    p = uri.find("/")
    p += 1
    name = uri[p:]

    os.putenv("IXC_MYAPP_TMP_DIR", "/tmp/ixcsys/%s" % name)
    os.putenv("IXC_MYAPP_CONF_DIR", "%s/ixc_configs/%s" % (sys_dir, name,))
    os.putenv("IXC_MYAPP_SCGI_PATH", "/tmp/ixcsys/%s/scgi.sock" % name)
    os.putenv("IXC_MYAPP_RELATIVE_DIR", uri)
    os.putenv("IXC_MYAPP_NAME", name)

    os.system(start_file)


def stop(uri: str):
    stop_file = "sh %s/%s/stop.sh" % (sys_dir, uri)
    os.putenv("IXC_MYAPP_DIR", "%s/%s" % (sys_dir, uri))

    p = uri.find("/")
    p += 1
    name = uri[p:]
    os.putenv("IXC_MYAPP_TMP_DIR", "/tmp/ixcsys/%s" % name)
    os.system(stop_file)

    path = "/tmp/ixcsys/%s" % name
    if not os.path.isdir(path): return
    spath = "%s/rpc.sock" % path
    if os.path.exists(spath): os.remove(spath)


import pywind.lib.proc as proc
import pywind.lib.netutils as netutil
import pywind.lib.configfile as conf

PID_PATH = "/tmp/ixcsys/ixcsys.pid"


def start_main(delay=0):
    if os.path.isfile(PID_PATH):
        print("the ixcsys process exists")
        return

    pid = os.fork()
    if pid != 0: sys.exit(0)

    os.setsid()
    os.umask(0)
    pid = os.fork()

    if pid != 0: sys.exit(0)

    if delay > 0: time.sleep(delay)
    cls = ixc_main_d()
    proc.write_pid(PID_PATH, os.getpid())
    try:
        cls.loop()
    except KeyboardInterrupt:
        stop_all()
    except:
        err = traceback.format_exc()
        sys.stderr.write("%s\r\n" % err)

    os.remove(PID_PATH)
    sys.exit(0)


def stop_main():
    pid = proc.get_pid(PID_PATH)

    if pid < 0:
        print("cannot found ixcsys process")
        return

    try:
        os.kill(pid, signal.SIGINT)
    except ProcessLookupError:
        os.remove(PID_PATH)


class ixc_main_d(object):
    __update_file_path = None
    __update_check_file = None
    __net_monitor_path = None
    __net_monitor_up_time = None
    __is_isset_rescue = None

    def get_systemctl_services(self):
        """获取所有的systemctl服务
        """
        services = []
        fdst = os.popen("systemctl list-unit-files")
        for line in fdst:
            line = line.replace("\n", "")
            line = line.replace("\r", "")
            _list = line.split(" ")
            if not _list: continue
            service = _list[0].strip()
            if service: services.append(service)

        fdst.close()
        return services

    def stop_os_NetworkManager(self):
        """停止操作系统的网络管理器
        :return:
        """
        services = [
            "NetworkManager.service",
            "connman.service"
        ]

        sys_services = self.get_systemctl_services()

        for service in services:
            if service not in sys_services: continue
            os.system("systemctl stop %s" % service)

    def get_if_ipaddr(self, ifname: str):
        """获取网卡IP地址
        :param ifname:
        :return:
        """
        cmd = "ip addr | grep %s | grep inet" % ifname
        fd = os.popen(cmd)
        s = fd.read()
        fd.close()
        s = s.strip()
        _list = s.split(" ")
        result = []
        for x in _list:
            if x: result.append(x)
        if not result: return None
        return netutil.parse_ip_with_prefix(result[1])

    def monitor_sys_network(self):
        """监控系统网络
        :return:
        """
        config = conf.ini_parse_from_file(self.__net_monitor_path)
        rescue_ifname = None

        for ifname in config:
            info = config[ifname]
            ipaddr = info["ipaddr"]
            is_rescued = bool(int(info.get("is_rescued", 0)))
            if is_rescued: rescue_ifname = ifname
            if_ipaddr = self.get_if_ipaddr(ifname)
            if not if_ipaddr and not is_rescued:
                os.system("ip link set %s up" % ifname)
                os.system("ip addr add %s dev %s" % (ipaddr, ifname))
        if not rescue_ifname:
            self.__net_monitor_up_time = time.time()
            return
        # 如果是应急网卡首先检查是否被设置
        if self.__is_isset_rescue: return

        interval = time.time() - self.__net_monitor_up_time

        if not self.__is_isset_rescue and interval < 30: return

        if_ipaddr = self.get_if_ipaddr("ixclanbr")
        if not if_ipaddr:
            # 首先检查是否设置了IP地址
            ip_info = self.get_if_ipaddr(rescue_ifname)
            # 如果存在IP信息那么先删除
            if ip_info:
                os.system("ip addr del %s/%s dev %s" % (ip_info[0], ip_info[1], rescue_ifname))
            os.system("ip link set %s up" % rescue_ifname)
            cmd = "ip addr add %s dev %s" % (config[rescue_ifname]["ipaddr"], rescue_ifname)
            os.system(cmd)
        self.__is_isset_rescue = True

    def __init__(self):
        self.__update_file_path = "/tmp/ixcsys_update.tar.gz"
        self.__update_check_file = "/tmp/ixcsys_update_check.md5"
        self.__net_monitor_path = "%s/net_monitor.ini" % sys_dir

        self.__net_monitor_up_time = time.time()
        self.__is_isset_rescue = False

        signal.signal(signal.SIGUSR1, self.sig_handle)
        signal.signal(signal.SIGTERM, self.sig_handle)

        if self.have_update(): self.do_update()

        self.stop_os_NetworkManager()
        time.sleep(5)
        start_all()

    def sig_handle(self, signum, frame):
        if signum == signal.SIGUSR1:
            self.restart()
            return

        if signum in (signal.SIGTERM,):
            stop_all()
            sys.exit(0)
        else:
            return

    def restart(self):
        """重启
        :return:
        """
        stop_all()
        self.__is_isset_rescue = False
        self.__net_monitor_up_time = time.time()
        time.sleep(30)
        # 检查是否有更新,有更新那么执行更新
        if self.have_update(): self.do_update()
        start_all()

    def loop(self):
        while 1:
            self.monitor_sys_network()
            time.sleep(30)

    def have_update(self):
        """检查是否有更新
        :return:
        """
        return os.path.isfile(self.__update_file_path)

    def check_os_env(self, fpath: str):
        """检查操作系统环境
        """
        if not os.path.isfile(fpath): return False

        with open(fpath, "r") as f:
            s = f.read()
        f.close()

        o = json.loads(s)

        dis, dis_id, release = os_info.get_os_info()

        if o["distributor_id"] != dis_id.lower(): return False
        if o["release"] != release.lower(): return False
        if o["arch"] != platform.machine().lower(): return False

        return True

    def do_update(self):
        d = "/tmp/ixcsys_update"

        if not os.path.isdir(d): os.mkdir(d)

        # MD5校验文件不存在那么禁止更新
        if not os.path.isfile(self.__update_check_file):
            print("UPDATE ERROR:not found update_check_file")
            return

        fdst = open(self.__update_check_file, "rb")
        file_md5 = fdst.read()
        fdst.close()

        md5 = hashlib.md5()
        fdst = open(self.__update_file_path, "rb")
        while 1:
            read = fdst.read(8192)
            if not read: break
            md5.update(read)
        fdst.close()

        if md5.digest() != file_md5:
            print("UPDATE ERROR:wrong update file md5")
            return

        os.system("tar xf %s -C %s" % (self.__update_file_path, d))
        os.chdir(d)

        if not self.check_os_env("host_info"):
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
        os.remove(self.__update_file_path)


def main():
    __helper = """
    start [app_uri] | stop [app_uri]  | debug app_uri | restart [app_uri] | service_start | force_stop_router
    """
    if not check_py_modules(): return
    if not os.path.isfile("/usr/bin/lsb_release"):
        print("ERROR:please install lsb_release")
        return
    if not os.path.isfile("/usr/sbin/in.tftpd"):
        print("ERROR:please install tftpd")
        return
    if len(sys.argv) < 2:
        print(__helper)
        return
    set_pub_env()
    action = sys.argv[1]
    if action not in ("start", "stop", "debug", "restart", "service_start", "force_stop_router"):
        print(__helper)
        return

    if len(sys.argv) == 3:
        uri = sys.argv[2]
    else:
        uri = ""

    if action == "force_stop_router":
        force_stop_router()
        return

    if not uri:
        if action == "start":
            start_main()
        elif action == "stop":
            stop_main()
            # stop_all()
        elif action == "service_start":
            start_main(delay=30)
        elif action == "debug":
            print(__helper)
        else:
            pid = proc.get_pid(PID_PATH)
            if pid < 0:
                start_main()
            else:
                os.kill(pid, signal.SIGUSR1)
        return

    if action in ("start", "debug",):
        if action == "debug":
            debug = True
        else:
            debug = False
        start(uri, debug=debug)
        return

    if action == "restart":
        stop(uri)
        start(uri)
        return

    stop(uri)


if __name__ == '__main__': main()
