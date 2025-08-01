#!/usr/bin/env python3

import os, sys, importlib, json, hashlib
import platform

BASE_DIR = os.path.dirname(sys.argv[0])

if not BASE_DIR: BASE_DIR = "."

sys.path.append(BASE_DIR)

import ixc_syslib.pylib.os_info as os_info

__builds = [
    "ixc_syscore/router",
    "ixc_syscore/sysadm",
    "ixc_syscore/DHCP",
    "ixc_syscore/DNS",
    "ixc_syscore/secDNS",
    "ixc_syscore/proxy",
    "ixc_syscore/init",
]

__helper = """
    help                            show help
    build build_name [cflags]       build software
    dev_build build_name [cflags]   build software for developer
    build_all [cflags]              build all
    install_lib                     install system library
    gen_update                      generate update archive
    gen_bin_install                 generate binary install package
    install install_name            install software name
    install_all prefix              install all
    rescue_install                  only replace ixc_main.py for update
    show_builds                     show build names
    proxy_rule_update               update proxy_rule
    app_data_update                 update application data directory
"""

INSTALL_PREFIX = "/opt/ixcsys"


def update_proxy_rule():
    """更新代理规则
    """
    files = [
        "ixc_configs/proxy/proxy_domain.txt",
        "ixc_configs/proxy/proxy_ip.txt",
        "ixc_configs/proxy/pass_ip.txt"
    ]
    for fpath in files:
        cmd = "cp %s /opt/ixcsys/%s" % (fpath, fpath,)
        os.system(cmd)


def app_data_update():
    files = [
        "shared_data/ca-bundle.crt",

        "ixc_syscore/DHCP/data/ipxe.efi",
        "ixc_syscore/DHCP/data/undionly.kpxe",
        "ixc_syscore/DHCP/data/oui.csv",
    ]

    for fpath in files:
        cmd = "cp %s /opt/ixcsys/%s" % (fpath, fpath,)
        os.system(cmd)


def __get_root_dir():
    abspath = os.path.abspath(__file__)
    root_dir = os.path.dirname(abspath)
    return root_dir


def __read_build_config():
    fpath = "build_config.json"
    if not os.path.isfile(fpath):
        print("ERROR:not found build configure file %s" % fpath)
        sys.exit(-1)

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


def __build(build_name, args: list, for_developer=False):
    if build_name not in __builds and not for_developer:
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
    ex_cflags = cfg.get("cflags", "")

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
        d = "-g -Wall -Wextra -Wno-unused-parameter"
    else:
        if ex_cflags.find("-O") != -1:
            d = ""
        else:
            d = "-O3 -g -Wall"

    cflags = " ".join([d, include, libdir, lib, ])
    cflags = cflags + " " + "".join(args[0:]) + " " + ex_cflags

    abspath = os.path.abspath(__file__)

    root_dir = os.path.dirname(abspath)

    try:
        m.build(root_dir, "%s/%s" % (root_dir, build_name,), cflags, debug=debug)
    except AttributeError:
        print("ERROR:not found build name %s build method from make.py" % build_name)
        return


def __build_all(args: list):
    for x in __builds:
        print("building %s" % x)
        __build(x, args)


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


def get_cp_cmd_version():
    """获取cp命令版本"""
    fdst = os.popen("cp --version | awk 'NR==1 {print $4}'")
    s = fdst.read().replace("\n", "")
    fdst.close()
    s = s.replace("\r", "")

    main_version, minor_version = s.split(".")

    return int(main_version), int(minor_version)


def __install_all(prefix=None):
    root_dir = __get_root_dir()
    if not prefix:
        prefix = INSTALL_PREFIX
    for x in __builds: __install(x, prefix=prefix)

    dirs = [
        "pywind",
        "ixc_syslib",
        "ixc_configs_bak",
        "ixc_configs",
        "shared_data",
    ]

    cp_cmd_version = get_cp_cmd_version()

    if cp_cmd_version[0] >= 9 and cp_cmd_version[1] >= 4:
        update_flags = "--update=none"
    else:
        update_flags = "-n"

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
            os.system("cp -r %s %s/%s/* %s" % (update_flags, root_dir, x, d))
        else:
            os.system("cp -r %s/%s/* %s" % (root_dir, x, d))

    files = [
        "ixc_cfg.py",
        "ixc_main.py",
        "net_monitor.ini",
        "version",
        #### 计划任务相关
        # PPPoE自动拨号
        "ixc_cron_pppoe_auto_redial.py",
        # 计划更新器
        "ixc_cron_updater.py",
    ]

    for x in files:
        if x == "net_monitor.ini":
            os.system("cp %s %s/%s %s" % (update_flags, root_dir, x, prefix))
        else:
            os.system("cp %s/%s %s" % (root_dir, x, prefix))
        ''''''


def __rescue_install():
    os.system("cp ixc_main.py %s" % INSTALL_PREFIX)


def gen_host_info(fpath: str):
    """生成主机信息
    """
    dis, dis_id, release = os_info.get_os_info()

    fdst = open(fpath, "w")

    o = {
        "distributor_id": dis_id.lower(),
        "release": release.lower(),
        "arch": platform.machine().lower()
    }
    fdst.write(json.dumps(o))
    fdst.close()


def __gen_update_archive():
    """生成更新归档,注意执行此函数需要先make install_all
    :return:
    """
    update_file = "/tmp/ixcsys_update.tar.gz"
    update_check_file = "/tmp/ixcsys_update_check.md5"
    # 生成一个临时安装目录
    prefix = "/tmp/ixc_update_temp"
    if not os.path.isdir(prefix): os.mkdir(prefix)
    __install_all(prefix=prefix)

    if not os.path.isdir(prefix):
        print("ERROR:not found install directory %s" % prefix)
        return

    gen_host_info("/tmp/ixc_update_temp/host_info")

    cur_dir = BASE_DIR
    os.chdir(prefix)
    os.system("tar czf %s ./*" % update_file)
    os.chdir(cur_dir)

    os.system("rm -rf %s" % prefix)

    if not os.path.isfile(update_file):
        print("ERROR:cannot generate %s" % update_file)
    # 计算文件MD5
    md5 = hashlib.md5()
    fdst = open(update_file, "rb")
    while 1:
        read = fdst.read(8192)
        if not read: break
        md5.update(read)
    fdst.close()

    fdst = open(update_check_file, "wb")
    fdst.write(md5.digest())
    fdst.close()

    print("generate update archive /tmp/ixcsys_update.tar.gz OK")


def install_lib():
    cmds = [
        "cp -r ixc_syslib %s" % INSTALL_PREFIX,
        "cp -r pywind %s" % INSTALL_PREFIX
    ]
    for cmd in cmds: os.system(cmd)


def build_binary_install_pkg():
    """构建二进制安装包
    """
    archive_path = "/tmp/ixcsys_update.tar.gz"

    ver_path = "%s/version" % os.path.dirname(os.path.abspath(__file__))
    dis, dis_id, release = os_info.get_os_info()

    __gen_update_archive()
    if not os.path.isfile(archive_path):
        print("ERROR:cannot found archive file")
        return
    with open("/tmp/ixcsys_update_check.md5", "rb") as f:
        md5_code = f.read()
    f.close()

    with open(ver_path, "r") as f:
        version = f.read()
    f.close()

    new_file = "/tmp/ixcsys-%s-%s-%s-%s.ixcpkg" % (dis_id, release, platform.machine(), version,)

    fdst_up = open(archive_path, "rb")

    fdst = open(new_file, "wb")
    fdst.write(b"ixcsys\n")
    fdst.write(md5_code)

    while 1:
        byte_data = fdst_up.read(8192)
        if not byte_data: break
        fdst.write(byte_data)
    fdst_up.close()
    fdst.close()

    pkg_path = "/tmp/ixcsys_pkg"
    if not os.path.isdir(pkg_path): os.mkdir(pkg_path)

    os.chdir(os.path.dirname(ver_path))
    # 清除旧的内容
    os.system("rm -rf %s/*" % pkg_path)
    os.system("mv %s %s" % (new_file, pkg_path,))

    fdst = open("ixc_bin_installer.py", "r")
    s = fdst.read()
    fdst.close()
    s = s.replace("{{PKG_FILE}}", "ixcsys-%s-%s-%s-%s.ixcpkg" % (dis_id, release, platform.machine(), version,))
    fdst = open("/tmp/ixcsys_pkg/ixc_bin_installer.py", "w")
    fdst.write(s)
    fdst.close()

    os.chdir("/tmp/ixcsys_pkg")

    fname = "ixcsys-%s-%s-%s-%s.bin.install.tar.gz" % (
        dis_id, release, platform.machine(), version,)

    os.system("tar czf /tmp/%s *" % fname)

    print("generate /tmp/%s OK" % fname)


def main():
    if len(sys.argv) < 2:
        print(__helper)
        return

    action = sys.argv[1]
    if action not in (
            "help", "build", "dev_build", "build_all", "install", "install_all", "show_builds", "gen_update",
            "rescue_install",
            "install_lib", "gen_bin_install", "proxy_rule_update", "app_data_update"):
        print(__helper)
        return

    if action == "help":
        print(__helper)
        return

    if action == "install_lib":
        install_lib()
        return
    if action == "gen_bin_install":
        build_binary_install_pkg()
        return

    if action in ("build", "dev_build",):
        if len(sys.argv) < 3:
            print(__helper)
            return
        if action == "dev_build":
            for_developer = True
        else:
            for_developer = False
        __build(sys.argv[2], sys.argv[3:], for_developer=for_developer)
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

    if action == "proxy_rule_update":
        update_proxy_rule()
        return

    if action == "app_data_update":
        app_data_update()
        return

    if action == "rescue_install":
        __rescue_install()
        return


if __name__ == '__main__': main()
