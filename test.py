#!/usr/bin/env python3

import ixc_syslib.pylib.RPCClient as client

rs = client.fn_call("DHCP", "/dhcp_client", "broadst_addr_get")
print(rs)
