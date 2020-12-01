#!/usr/bin/env python3

import pywind.lib.configfile as conf

print(conf.ini_parse_from_file("ixc_configs/DHCP/dhcp_server.ini"))