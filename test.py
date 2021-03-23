#!/usr/bin/env python3

import ixc_syslib.pylib.RPCClient as RPC

port_map_configs = RPC.fn_call("router", "/config", "port_map_configs_get")
