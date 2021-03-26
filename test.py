#!/usr/bin/env python3

import ixc_syslib.pylib.RPCClient as RPC

ip6addr="2607:f8b0:4007:800::2004"

rs=RPC.fn_call("router", "/runtime", "add_route", "2607:f8b0:4007:800::2004", 128, "::", is_ipv6=True)
print(rs)
