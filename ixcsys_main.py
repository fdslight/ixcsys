#!/usr/bin/env python3
import os, sys

sys_dir = os.path.dirname(os.path.abspath(__file__))

sys.path.append(sys_dir)

# 必须要启动的服务
must_services = [
    "ixc_syscore/sysadm", "ixc_syscore/router"
]

def main():
    conf_dir = "%s/ixc_configs" % sys_dir
    app_dir = "%s/ixc_apps"
    sys_py_interpreter = sys.executable

    os.putenv("IXC_SYS_DIR", sys_dir)
    os.putenv("IXC_CONF_DIR", conf_dir)
    os.putenv("IXC_APP_DIR", app_dir)
    os.putenv("IXC_PYTHON", sys_py_interpreter)

    if not os.path.isdir("/tmp/ixcsys"): os.mkdir("/tmp/ixcsys")

    for x in must_services:
        path = "sh %s/%s/start.sh" % (sys_dir, x,)
        os.putenv("IXC_MYAPP_DIR", "%s/%s" % (sys_dir, x,))
        os.system(path)


if __name__ == '__main__': main()
