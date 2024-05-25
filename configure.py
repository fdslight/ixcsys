#!/usr/bin/env python3

import getopt, sys, os, json

__helper = """
action:
    nodebug              set no debug build environment
    debug                st debug build environment
    help                 print help

default or debug optional arguments:
    --python3_include    python3 incldue
    --python3_lib        python3 library path
    --cflags             gcc flags
"""

include_dirs = [
]

lib_dirs = []
libs = []


def get_shared_object_fname(fpath: str, prefix: str):
    """根据文件前缀获取共享库名称
    """
    _list = os.listdir(fpath)
    result = ""

    for x in _list:
        path = "%s/%s" % (fpath, x)
        if not os.path.isfile(path): continue
        if x[0:3] != "lib": continue
        p = x.find(".so")
        if p < 4: continue
        p = x.find(prefix)
        if p != 0: continue
        result = x
        break

    return result


def have_pkg_config():
    """查找是否有pkg-config
    """
    fdst = os.popen("which pkg-config")
    s = fdst.read()
    fdst.close()

    if not s: return False

    return True


def gen_build_config(debug, cflags):
    for d in include_dirs:
        if not os.path.isdir(d):
            print("ERROR:directory %s not exists" % d)
            return
        ''''''
    for d in lib_dirs:
        if not os.path.isdir(d):
            print("ERROR:directory %s not exists" % d)
            return
        so_name = get_shared_object_fname(d, "libpython3")
        if so_name in libs: continue
        p = so_name.find(".so")
        libs.append(so_name[0:p][3:])

    build_config = {"debug": debug,
                    "c_includes": include_dirs,
                    "libs": libs,
                    "lib_dirs": lib_dirs,
                    "cflags": cflags
                    }

    for d in build_config["c_includes"]:
        if not os.path.isdir(d):
            print("ERROR:Not found directory %s" % d)
            return
        ''''''
    fdst = open("build_config.json", "w")
    fdst.write(json.dumps(build_config))
    fdst.close()

    print("configure OK")


def config_default(cflags,debug=False):
    if not have_pkg_config():
        print("not found pkg-config")
        return

    fdst = os.popen("pkg-config python3 --libs --cflags")
    cmd = fdst.read()
    fdst.close()
    cmd = cmd.replace("-I", "")
    cmd = cmd.replace("\n", "")
    _lib_dirs = cmd.replace("include", "lib").split(" ")
    lib_dirs = []
    libname = "python3"

    for s in _lib_dirs:
        p = s.find("/python")
        if p <= 0: continue
        lib_dirs.append(s[0:p])
        p += 1
        libname = s[p:]

    _includes = cmd.split(" ")
    includes = []
    for s in _includes:
        s = s.strip()
        if not s: continue
        includes.append(s)

    build_config = {"debug": debug,
                    "c_includes": includes,
                    "libs": [libname],
                    "lib_dirs": lib_dirs,
                    "cflags":cflags,
                    }

    fdst = open("build_config.json", "w")
    fdst.write(json.dumps(build_config))
    fdst.close()

    print("configure OK")


def main():
    # 检查必须的二进制文件是否存在
    if not os.path.isfile("/usr/bin/lsb_release"):
        print("ERROR:please install lsb_release")
        return
    if not os.path.isfile("/usr/bin/curl"):
        print("ERROR:please install curl")
        return
    if not os.path.isfile("/usr/sbin/in.tftpd"):
        print("ERROR:please install tftpd")
        return

    try:
        opts, args = getopt.getopt(sys.argv[2:], "", ["python3_include=", "python3_lib=", "cflags="])
    except getopt.GetoptError:
        print(__helper)
        return

    if len(sys.argv) < 2:
        print(__helper)
        return

    if sys.argv[1] not in ("debug","nodebug","help",):
        print(__helper)
        return

    if sys.argv[1]=="help":
        print(__helper)
        return

    debug = False
    if sys.argv[1]=="debug":
        debug=True
    cflags = ""

    for name, value in opts:
        if name == "--python3_include":
            include_dirs.append(value)
            continue
        if name == "--python3_lib":
            lib_dirs.append(value)
            continue
        if name == "--help":
            print(__helper)
            return
        if name == "--cflags":
            cflags = value
            continue
        ''''''

    if not include_dirs or not lib_dirs:
        if not include_dirs:
            print("NOTIFY:because of not set python3_include directory,use system default")
        if not lib_dirs:
            print("NOTIFY:because of not set python3_lib directory,use system default")
        config_default(cflags,debug=debug)
        return
        
    gen_build_config(debug, cflags)


if __name__ == '__main__': main()
