#!/usr/bin/env python3
import socket,os

# import ixc_syslib.pylib.RPCClient as RPCClient

"""
rand_key = os.urandom(16)
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.bind(("127.0.0.1", 0))
port = s.getsockname()[1]

RPCClient.fn_call("router", "/netpkt", "unset_fwd_port", 3)
ok, message = RPCClient.fn_call("router", "/netpkt", "set_fwd_port", 3,
                                rand_key, port)

RPCClient.fn_call("router", "/runtime", "vsw_enable", True)
while 1:
    msg, addr = s.recvfrom(4096)
    link_data = msg[20:]
    src_hwaddr = "%s:%s:%s:%s:%s:%s" % (
        hex(link_data[0]), hex(link_data[1]), hex(link_data[2]), hex(link_data[3]), hex(link_data[4]),
        hex(link_data[5]))
    dst_hwaddr = "%s:%s:%s:%s:%s:%s" % (
        hex(link_data[6]), hex(link_data[7]), hex(link_data[8]), hex(link_data[9]), hex(link_data[10]),
        hex(link_data[11]))
    protocol, = struct.unpack("!H", link_data[12:14])
    print(src_hwaddr, dst_hwaddr, hex(protocol))

s.close()
"""
"""
message = RPCClient.fn_call("DHCP", "/dhcp_server", "set_dhcp_option", 138,
                            socket.inet_pton(socket.AF_INET, "192.168.2.60"))

print(message)
"""
"""
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.connect(("192.168.0.1", 53))
sent = bytes(42)

for i in range(10000000):
    try:
        s.send(sent)
    except KeyboardInterrupt:
        break
    except:
        pass
s.close()
"""


def check_dns_rule(text: str):
    _list = text.split("\n")
    for s in _list:
        s = s.replace("\r", "")
        s = s.strip()
        if not s: continue
        if s[0] == "#": continue
        p = s.find(":")
        if p < 1:
            return False, s
        host = s[0:p].strip()
        p += 1
        try:
            action = int(s[p:].strip())
        except ValueError:
            return False, s
        if action not in (0, 1, 2,):
            return False, s

    return True, None

fdst=open("ixc_configs/proxy/proxy_domain.txt","r")
text=fdst.read()
fdst.close()

print(check_dns_rule(text))