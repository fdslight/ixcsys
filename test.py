#!/usr/bin/env python3


from ixc_syscore.DNS.pylib import rule
import ixc_syscore.proxy.pylib.file_parser as file_parser

rules = file_parser.parse_host_file("proxy_domain.txt")
m = rule.matcher()

for r in rules:
    host, n = r
    action = "encrypt"
    if n == 2:
        action = "drop"
    if n == 0:
        action = "encrypt"
    if n == 1:
        action = "proxy"

    rs=m.match(host)
    m.add_rule(host, action)

