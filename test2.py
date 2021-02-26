#!/usr/bin/env python3

import socket, os, sys

fpath = "test.file"

if not os.path.isfile(fpath):
    byte_data = os.urandom(1240)
    with open(fpath, "wb") as f:
        f.write(byte_data)
    f.close()
else:
    with open(fpath, "rb") as f:
        byte_data = f.read()
    f.close()

s = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
s.bind(("::", 4444))

n = 0
x = len(byte_data)
while n < x:
    print("%s %s %s %s %s %s %s %s" % (
        hex(byte_data[n]), hex(byte_data[n + 1]), hex(byte_data[n + 2]), hex(byte_data[n + 3]), hex(byte_data[n + 4]),
        hex(byte_data[n + 5]),
        hex(byte_data[n + 6]), hex(byte_data[n + 7])))
    n += 8
    if n == 1232: print("---------------")

s.sendto(byte_data, ("4444::1", 4444))
print(s.recv(4096))
s.close()
