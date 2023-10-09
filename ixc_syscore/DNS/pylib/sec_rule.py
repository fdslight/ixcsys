#!/usr/bin/env python3
import os


def parse_from_text(text: str):
    text = text.replace("\r", "")
    _list = text.split("\n")
    _list2 = []
    for s in _list:
        s = s.strip()
        if not s: continue
        _list2.append(s)

    return _list2


def parse_from_file(fpath: str):
    if not os.path.isfile(fpath): return []

    with open(fpath, "r") as f:
        s = f.read()
    f.close()

    return parse_from_text(s)


def save_to_file(rules, fpath: str):
    fdst = open(fpath, "w")
    for x in rules:
        s = "%s\r\n" % x
        fdst.write(s)
    fdst.close()
