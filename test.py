#!/usr/bin/env python3
import socket, os, struct, time

import ixc_syslib.pylib.RPCClient as RPCClient

rand_key = os.urandom(16)
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.bind(("127.0.0.1", 0))
port = s.getsockname()[1]

RPCClient.fn_call("router", "/config", "unset_fwd_port", 7)
ok, message = RPCClient.fn_call("router", "/config", "set_fwd_port", 7,
                                rand_key, port)

while 1:
    msg, addr = s.recvfrom(4096)
    print(msg,addr)
    break
