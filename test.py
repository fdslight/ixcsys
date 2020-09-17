#!/usr/bin/env python3

import ixc_syslib.pylib.RPCClient as client

rs = client.fn_call("sysadm", "/WAN/dhcp_client", "dhcp_client_enable", False)
print(rs)
