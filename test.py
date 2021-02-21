#!/usr/bin/env python3

import socket, os, time

s = socket.socket()
s.connect(("8.8.8.8", 8800))

block_size = 1024
cnt = 12800
seq = []

for i in range(cnt):
    t = os.urandom(block_size)
    seq.append(t)

begin = time.time()

for i in range(cnt):
    s.send(seq[i])
    print("send ", i + 1)
    _ = s.recv(4096)
    print("recv ", i + 1)

t = time.time() - begin
speed = block_size * cnt / t
print("%s byte/s" % speed)
s.close()

"""
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

for i in range(2):
    byte_data=os.urandom(1024)
    s.sendto(byte_data,("8.8.8.8", 443))
    print(byte_data)
    print(s.recvfrom(4096))

s.close()
"""
