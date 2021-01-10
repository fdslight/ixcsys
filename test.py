#!/usr/bin/env python3

import socket

s = socket.socket()
s.connect(("8.8.8.8", 8800))
s.send(b"hello,wolrd")
s.close()
