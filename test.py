#!/usr/bin/env python3

import ixc_syslib.pylib.RPCClient as client

rs = client.fn_call("router", "/netpkt", "get_server_recv_port")
print(rs)
rs = client.fn_call("router", "/runtime", "get_all_pkt_flags")
print(rs)