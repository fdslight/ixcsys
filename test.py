#!/usr/bin/env python3

import ixc_syslib.pylib.RPCClient as RPC
import socket

ip6addr = "2001::1f0d:4217"

rs = RPC.fn_call("router", "/runtime", "add_route", "2607:f8b0:4007:800::2004", 128, "::", is_ipv6=True)

s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
s.connect((ip6addr, 443))
s.send(b"hello,test IPv6 tcp");
print(s.recv(2048))
s.close()
