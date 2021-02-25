#!/usr/bin/env python3

import socket, os

s = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
s.connect(("8888::2", 4444))
s.send(os.urandom(2048))
s.close()
