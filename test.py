#!/usr/bin/env python3

import ixc_syslib.pylib.RPCClient as RPC
import socket

wan_ip6info = RPC.fn_call("router", "/runtime", "get_lan_ipaddr_info", is_ipv6=True)
print(wan_ip6info)