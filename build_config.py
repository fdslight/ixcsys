#!/usr/bin/env python3

import getopt, sys, os, json

__helper = """
    --python3_include    python3 incldue
    --debug              debug mode
    --help               print help
"""

include_dirs = [

]


def gen_build_config(debug):
    build_config = {"debug": debug,
                    "c_includes": include_dirs,
                    "libs": [],
                    "lib_dirs": []
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
        opts, args = getopt.getopt(sys.argv[1:], "", ["python3_include=", "with_debug", "help"])
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
        if name == "--with_debug":
            debug = True
            continue
        if name == "--help":
            print(__helper)
            return

    gen_build_config(debug)


if __name__ == '__main__': main()
