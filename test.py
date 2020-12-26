#!/usr/bin/env python3

import socket

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.connect(("8.8.8.8", 8800))
s.send(b"hello,world")
s.close()
