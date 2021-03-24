#!/usr/bin/env python3

import ixc_syslib.pylib.RPCClient as RPC

protocol = "ALL"

seq = list(bytes(0xff))
if protocol == "UDP" or protocol == "ALL":
    seq[17] = 1
if protocol == "TCP" or protocol == "ALL":
    seq[6] = 1
if protocol == "UDPLite" or protocol == "ALL":
    seq[136] = 1

byte_data = bytes(seq)

print(len(byte_data))