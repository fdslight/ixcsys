#!/usr/bin/env python3
import os, sys

sys_dir = os.path.dirname(os.path.abspath(__file__))

sys.path.append(sys_dir)

# 必须要启动的服务
must_services = [
    "ixc_syscore/sysadm", "ixc_syscore/router"
]


def set_pub_env():
    conf_dir = "%s/ixc_configs" % sys_dir
    app_dir = "%s/ixc_apps"
    sys_py_interpreter = sys.executable

    os.putenv("IXC_SYS_DIR", sys_dir)
    os.putenv("IXC_CONF_DIR", conf_dir)
    os.putenv("IXC_APP_DIR", app_dir)
    os.putenv("IXC_PYTHON", sys_py_interpreter)

    if not os.path.isdir("/tmp/ixcsys"): os.mkdir("/tmp/ixcsys")


def start_all():
    for x in must_services: start(x)


def stop_all():
    for x in must_services: stop(x)


def start(uri: str):
    start_file = "sh %s/%s/start.sh" % (sys_dir, uri)
    os.putenv("IXC_MYAPP_DIR", "%s/%s" % (sys_dir, uri))

    p = uri.find("/")
    p += 1
    name = uri[p:]
    os.putenv("IXC_MYAPP_TMP_DIR", "/tmp/ixcsys/%s" % name)
    os.system(start_file)


def stop(uri: str):
    stop_file = "sh %s/%s/stop.sh" % (sys_dir, uri)
    os.putenv("IXC_MYAPP_DIR", "%s/%s" % (sys_dir, uri))

    p = uri.find("/")
    p += 1
    name = uri[p:]
    os.putenv("IXC_MYAPP_TMP_DIR", "/tmp/ixcsys/%s" % name)
    os.system(stop_file)


def main():
    __helper = """
    start | stop [app_uri]
    """
    if len(sys.argv) < 2:
        print(__helper)
        return
    set_pub_env()
    action = sys.argv[1]
    if action not in ("start", "stop",):
        print(__helper)
        return

    if len(sys.argv) == 3:
        uri = sys.argv[2]
    else:
        uri = ""

    if not uri:
        if action == "start":
            start_all()
        else:
            stop_all()
        return

    if action == "start":
        start(uri)
    else:
        stop(uri)


if __name__ == '__main__': main()
