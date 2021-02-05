#!/usr/bin/env python3

import socket, os, time

s = socket.socket()
s.connect(("8.8.8.8", 8800))

block_size = 1024
cnt = 10
seq = []

for i in range(cnt):
    t = os.urandom(block_size)
    seq.append(t)

begin = time.time()
for i in range(cnt):
    s.send(seq[i])
    _ = s.recv(4096)

t = time.time() - begin
speed = block_size * cnt / t
print("%s byte/s" % speed)
s.close()
