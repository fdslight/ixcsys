#!/usr/bin/env python3

import os, sys, importlib, json

BASE_DIR = os.path.dirname(sys.argv[0])

if not BASE_DIR: BASE_DIR = "."

sys.path.append(BASE_DIR)

__builds = [
    "ixc_syscore/router",
    "ixc_syscore/sysadm",
    "ixc_syscore/DHCP",
    "ixc_syscore/DNS",
    "ixc_syscore/tftp",
    "ixc_syscore/proxy",
    "ixc_syscore/init",
]

__helper = """
    help                            show help
    build build_name [cflags]       build software
    build_all [cflags]              build all
    gen_update                      generate update archive
    install install_name            install software name
    install_all prefix              install all
    show_builds                     show build names
"""

INSTALL_PREFIX = "/opt/ixcsys"


def __get_root_dir():
    abspath = os.path.abspath(__file__)
    root_dir = os.path.dirname(abspath)
    return root_dir


def __read_build_config():
    fpath = "build_config.json"

    if not os.path.isfile(fpath):
        o = {
            "debug": True,
            "c_includes": [
                ""
            ],
            "libs": [
            ],
            "lib_dirs": [

            ]
        }
        return o

    with open(fpath, "r") as f:
        s = f.read()
    f.close()

    o = json.loads(s)

    return o


def build_config_args(insert_s: str, _list: list):
    results = []
    for s in _list:
        results.append("%s %s" % (insert_s, s))

    return " ".join(results)


def __build(build_name, args: list):
    if build_name not in __builds:
        print("ERROR:not found build name %s" % build_name)
        return

    name = "%s.make" % build_name.replace("/", ".")

    try:
        importlib.import_module(name)
    except ImportError:
        print("ERROR:not found build name %s make.py file" % build_name)
        return

    cfg = __read_build_config()
    debug = cfg["debug"]
    c_includes = cfg["c_includes"]
    libdirs = cfg["lib_dirs"]
    libs = cfg["libs"]

    m = sys.modules[name]

    if c_includes:
        include = build_config_args("-I", c_includes)
    else:
        include = ""

    if libdirs:
        libdir = build_config_args("-L", libdirs)
    else:
        libdir = ""

    if libs:
        lib = build_config_args("-l", libs)
    else:
        lib = ""

    if debug:
        d = "-g -Wall"
    else:
        d = ""

    cflags = " ".join([d, include, libdir, lib, ])
    cflags = cflags + " " + "".join(args[1:])

    abspath = os.path.abspath(__file__)

    root_dir = os.path.dirname(abspath)

    try:
        m.build(root_dir, "%s/%s" % (root_dir, build_name,), cflags, debug=debug)
    except AttributeError:
        print("ERROR:not found build name %s build method from make.py" % build_name)
        return


def __build_all(args: list):
    for x in __builds: __build(x, args)


def __install(app_name: str, prefix=None):
    root_dir = __get_root_dir()
    if not prefix:
        prefix = INSTALL_PREFIX

    name = "%s.make" % app_name.replace("/", ".")
    try:
        importlib.import_module(name)
    except ImportError:
        print("ERROR:not found build name %s make.py file" % app_name)
        return
    m = sys.modules[name]
    try:
        m.install(root_dir, prefix, app_name)
    except:
        print("cannot install for %s" % app_name)
        return
    if not os.path.isdir(prefix):
        try:
            os.mkdir(prefix)
        except:
            print("ERROR:cannot create directory %s for %s" % (prefix, app_name))
            return
        ''''''
    ''''''


def __install_all(prefix=None):
    root_dir = __get_root_dir()
    if not prefix:
        prefix = INSTALL_PREFIX
    for x in __builds: __install(x,prefix=prefix)

    dirs = [
        "pywind",
        "ixc_syslib",
        "ixc_configs_bak",
        "ixc_apps",
        "ixc_configs"
    ]
    for x in dirs:
        d = "%s/%s" % (prefix, x)
        if not os.path.isdir(d):
            try:
                os.mkdir(d)
            except:
                print("ERROR:cannot create directory %s" % d)
                return
            ''''''
        if x == "ixc_configs":
            # 不重写配置文件
            os.system("cp -r -n %s/%s/* %s" % (root_dir, x, d))
        else:
            os.system("cp -r %s/%s/* %s" % (root_dir, x, d))

    files = [
        "ixc_cfg.py",
        "ixc_main.py",
        "net_monitor.ini",
        "version",
    ]

    for x in files:
        if x == "net_monitor.ini":
            os.system("cp -n %s/%s %s" % (root_dir, x, prefix))
        else:
            os.system("cp %s/%s %s" % (root_dir, x, prefix))


def __gen_update_archive():
    """生成更新归档,注意执行此函数需要先make install_all
    :return:
    """
    # 生成一个临时安装目录
    prefix = "/tmp/ixc_update_temp"
    if not os.path.isdir(prefix): os.mkdir(prefix)
    __install_all(prefix=prefix)

    if not os.path.isdir(prefix):
        print("ERROR:not found install directory %s" % prefix)
        return

    cur_dir = BASE_DIR
    os.chdir(prefix)
    os.system("tar czf /tmp/ixcsys_update.tar.gz ./*")
    os.chdir(cur_dir)

    os.system("rm -rf %s" % prefix)

    print("generate update archive /tmp/ixcsys_update.tar.gz OK")


def main():
    if len(sys.argv) < 2:
        print(__helper)
        return

    action = sys.argv[1]
    if action not in ("help", "build", "build_all", "install", "install_all", "show_builds", "gen_update"):
        print(__helper)
        return

    if action == "help":
        print(__helper)
        return

    if action == "build":
        if len(sys.argv) < 3:
            print(__helper)
            return
        __build(sys.argv[2], sys.argv[3:])
        return

    if action == "build_all":
        __build_all(sys.argv[2:])
        return

    if action == "install":
        if len(sys.argv) != 3:
            print(__helper)
            return
        __install(sys.argv[2])
        return

    if action == "install_all":
        __install_all()
        return

    if action == "show_builds":
        for s in __builds: print(s)
        return

    if action == "gen_update":
        __gen_update_archive()
        return


if __name__ == '__main__': main()
