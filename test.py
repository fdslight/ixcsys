#!/usr/bin/env python3
import ixc_syslib.pylib.RPCClient as RPCClient

client = RPCClient.RPCClient("sysadm")

client.send_request("/WAN", b"")
r = client.get_result()
print(r)
