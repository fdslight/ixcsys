#!/usr/bin/env python3

import time, traceback, sys, socket, pickle, os, io

# 一般的信息
LEVEL_INFO = 0
# 告警信息
LEVEL_ALERT = 1
# 错误信息
LEVEL_ERR = 2

LEVELS = (
    LEVEL_INFO, LEVEL_ALERT, LEVEL_ERR,
)


def syslog_write(name: str, message: str, level=LEVEL_INFO):
    if level not in LEVELS:
        raise ValueError("wrong argument value for level")
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("127.0.0.1", 514))

    o = {
        "level": level,
        "name": name,
        "message": message
    }
    s.send(pickle.dumps(o))
    s.close()


def print_error(text="", debug=False):
    s1 = "<error time='%s'>" % time.strftime("%Y-%m-%d %H:%M:%S %Z")
    s2 = "</error>\r\n"

    if text:
        text = "%s\r\n%s\r\n%s\r\n" % (s1, text, s2,)
    else:
        excpt = traceback.format_exc()
        text = "%s\r\n%s\r\n%s\r\n" % (s1, excpt, s2)

    app_name = os.getenv("IXC_MYAPP_NAME")
    if not app_name or debug:
        sys.stderr.write(text)
        sys.stderr.flush()
        return
    syslog_write(app_name, text, level=LEVEL_ERR)


def print_info(text, debug=False):
    app_name = os.getenv("IXC_MYAPP_NAME")
    if not app_name or debug:
        sys.stdout.write(text)
        sys.stdout.flush()
        return

    syslog_write(app_name, text, level=LEVEL_INFO)


def print_alert(text,debug=False):
    app_name = os.getenv("IXC_MYAPP_NAME")
    if not app_name or debug:
        sys.stdout.write(text)
        sys.stdout.flush()
        return

    syslog_write(app_name, text, level=LEVEL_ALERT)


class stdout(io.StringIO):
    def write(self, s):
        print_info(s)
        return len(s)

    def writelines(self, lines):
        s = "".join(lines)
        print_info(s)


class stderr(io.StringIO):
    def write(self, s):
        print_error(s)
        return len(s)

    def writelines(self, lines):
        s = "".join(lines)
        print_error(s)
