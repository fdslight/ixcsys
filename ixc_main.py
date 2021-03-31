#!/usr/bin/env python3
import os, sys, signal, time, traceback

sys_dir = os.path.dirname(os.path.abspath(__file__))

sys.path.append(sys_dir)

# 必须要启动的服务
must_services = [
    "ixc_syscore/init",
    "ixc_syscore/router",
    "ixc_syscore/sysadm",
    "ixc_syscore/DHCP",
    "ixc_syscore/DNS",
    "ixc_syscore/tftp",
    "ixc_syscore/proxy",
]


def set_pub_env():
    conf_dir = "%s/ixc_configs" % sys_dir
    app_dir = "%s/ixc_apps" % sys_dir
    sys_py_interpreter = sys.executable

    os.putenv("IXC_SYS_DIR", sys_dir)
    os.putenv("IXC_CONF_DIR", conf_dir)
    os.putenv("IXC_APP_DIR", app_dir)
    os.putenv("IXC_PYTHON", sys_py_interpreter)
    os.putenv("IXC_SYSROOT", sys_dir)

    if not os.path.isdir("/tmp/ixcsys"): os.mkdir("/tmp/ixcsys")


def start_all():
    for x in must_services: start(x, debug=False)


def stop_all():
    _list = must_services.copy()
    _list.reverse()
    for x in _list: stop(x)


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


import pywind.lib.proc as proc

PID_PATH = "/tmp/ixcsys/ixcsys.pid"


def start_main():
    if os.path.isfile(PID_PATH):
        print("the ixcsys process exists")
        return

    pid = os.fork()
    if pid != 0: sys.exit(0)

    os.setsid()
    os.umask(0)
    pid = os.fork()

    if pid != 0: sys.exit(0)
    proc.write_pid(PID_PATH, os.getpid())

    cls = ixc_main_d()
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

    def __init__(self):
        self.__update_file_path = "/tmp/ixcsys_update.tar.gz"
        signal.signal(signal.SIGUSR1, self.sig_handle)
        if self.have_update():
            self.do_update()
        start_all()

    def sig_handle(self, signum, frame):
        if signum == signal.SIGUSR1:
            self.restart()
            return
        stop_all()
        sys.exit(0)

    def restart(self):
        """重启
        :return:
        """
        stop_all()
        time.sleep(30)
        # 检查是否有更新,有更新那么执行更新
        if self.have_update(): self.do_update()
        start_all()

    def loop(self):
        while 1: time.sleep(60)

    def have_update(self):
        """检查是否有更新
        :return:
        """
        return os.path.isfile(self.__update_file_path)

    def do_update(self):
        d = "/tmp/ixcsys_update"

        if not os.path.isdir(d): os.mkdir(d)

        os.system("tar xf %s -C %s" % (self.__update_file_path, d))
        os.chdir(d)

        _list = os.listdir(".")

        for x in _list:
            if x == "ixc_configs":
                os.system("cp -r -n ixc_configs %s" % sys_dir)
            else:
                os.system("cp -r %s %s" % (x, sys_dir))
            """"""
        os.system("rm -rf ./*")
        os.remove(self.__update_file_path)


def main():
    __helper = """
    start [app_uri] | stop [app_uri] | force_stop | debug app_uri | restart [app_uri] | systemd_start
    """
    if len(sys.argv) < 2:
        print(__helper)
        return
    set_pub_env()
    action = sys.argv[1]
    if action not in ("start", "stop", "debug", "restart", "force_stop", "systemd_start",):
        print(__helper)
        return

    if len(sys.argv) == 3:
        uri = sys.argv[2]
    else:
        uri = ""

    if action == "force_stop":
        stop_all()
        return

    if action == "systemd_start":
        time.sleep(60)
        start_main()
        return

    if not uri:
        if action == "start":
            start_main()
        elif action == "stop":
            stop_main()
            # stop_all()
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
