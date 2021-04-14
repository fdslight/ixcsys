#!/usr/bin/env python3

import getopt, sys, os, json

__helper = """
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
    """根据文件前缀获取共享哭名称
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
        result = x[0:p]
        break

    return result


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
        libs.append(so_name[0:-3][3:])

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


def main():
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
