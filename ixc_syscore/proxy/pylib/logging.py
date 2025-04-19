#!/usr/bin/env python3

import time, traceback, sys

import ixc_syslib.pylib.logging as _logging


def print_general(text, address):
    s = "%s\t%s:%s" % (text, address[0], address[1])
    _logging.print_alert(s)


def print_error(text=""):
    if not text:
        text = traceback.format_exc()

    _logging.print_error(text)
