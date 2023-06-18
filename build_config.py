#!/usr/bin/env python3

import getopt, sys, os, json

__helper = """
    default              auto set default build environment
    default_debug        auto set default build debug environment
    help                 print help
    --python3_include    python3 incldue
    --python3_lib        python3 library path
    --debug              debug mode
    --help               print help
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


def gen_build_config(debug):
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
                    "lib_dirs": lib_dirs
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


def config_default(debug=False):
    if not have_pkg_config():
        print("not found pkg-config")
        return

    fdst = os.popen("pkg-config python3 --libs --cflags")
    cmd = fdst.read()
    fdst.close()
    cmd = cmd.replace("-I", "")
    cmd = cmd.replace("\n", "")
    _lib_dirs = cmd.replace("include", "lib").split(" ")
    lib_dirs=[]
    libname="python3"

    for s in _lib_dirs:
        p = s.find("/python")
        if p <= 0: continue
        lib_dirs.append(s[0:p])
        p+=1
        libname=s[p:]

    includes = cmd.split(" ")

    build_config = {"debug": debug,
                    "c_includes": includes,
                    "libs": [libname],
                    "lib_dirs": lib_dirs
                    }

    fdst = open("build_config.json", "w")
    fdst.write(json.dumps(build_config))
    fdst.close()

    print("configure OK")


def main():
    if not os.path.isfile("/usr/bin/lsb_release"):
        print("ERROR:please install lsb_release")
        return
    if len(sys.argv) == 2:
        if sys.argv[1] == "default":
            config_default(debug=False)
        elif sys.argv[1] == "help":
            print(__helper)
        elif sys.argv[1] == "default_debug":
            config_default(debug=True)
        else:
            print(__helper)
        return
    try:
        opts, args = getopt.getopt(sys.argv[1:], "", ["python3_include=", "python3_lib=", "with_debug", "help"])
    except getopt.GetoptError:
        print(__helper)
        return

    if len(sys.argv) < 2:
        print(__helper)
        return

    debug = False

    for name, value in opts:
        if name == "--python3_include":
            include_dirs.append(value)
            continue
        if name == "--python3_lib":
            lib_dirs.append(value)
            continue
        if name == "--with_debug":
            debug = True
            continue
        if name == "--help":
            print(__helper)
            return

    gen_build_config(debug)


if __name__ == '__main__': main()
