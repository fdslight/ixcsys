#!/usr/bin/env python3
import socket, os, struct

import ixc_syslib.pylib.RPCClient as RPCClient

rand_key = os.urandom(16)
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.bind(("127.0.0.1", 0))
port = s.getsockname()[1]

RPCClient.fn_call("router", "/config", "unset_fwd_port", 7)
ok, message = RPCClient.fn_call("router", "/config", "set_fwd_port", 7,
                                rand_key, port)

RPCClient.fn_call("router", "/config", "traffic_cpy_enable", True)

while 1:
    msg, addr = s.recvfrom(4096)
    print(struct.unpack("!I",msg[20:24]), addr)
    break
RPCClient.fn_call("router", "/config", "traffic_cpy_enable", False)
s.close()

"""
message = RPCClient.fn_call("DHCP", "/dhcp_server", "set_dhcp_option", 138,
                            socket.inet_pton(socket.AF_INET, "192.168.2.60"))

print(message)
"""
"""
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.connect(("192.168.0.1", 53))
sent = bytes(42)

for i in range(10000000):
    try:
        s.send(sent)
    except KeyboardInterrupt:
        break
    except:
        pass
s.close()
"""
