#!/usr/bin/env python3

a = 0xffff_ffff
b = 0xff

v = (a - b) & 0xffff_ffff

print(hex(v))
