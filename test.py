#!/usr/bin/env python3

import ixc_syslib.pylib.RPCClient as client

rs = client.fn_call("router", "/WAN/dhcp_client", "dhcp_client_enable", True)
print(rs)
