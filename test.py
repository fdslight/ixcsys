#!/usr/bin/env python3

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
client = croc.RPCClient("/tmp/ixcsys/router/rpc.sock")
client.fn_call("hello")
"""
"""
message = RPCClient.fn_call("router", "/config", "wan_config_get")

print(message)
"""


# import pywind.lib.netutils as netutils

# print(netutils.calc_subnet("91.108.56.0",22))

def __parse_oui_corp(s: bytes):
    """解析厂商
    """
    _list = s.split(b"\r\n")
    if not _list: return None
    ss = _list.pop(0).decode()
    p = ss.find("(hex)")
    prefix = ss[0:p].strip().replace("\t", "")
    p += 5
    corp = ss[p:].strip().replace("\t", "")

    return prefix, corp


def parse_oui(path: str):
    """解析MAC OUI文件
    """
    fdst = open(path, "rb")
    s = fdst.read()
    fdst.close()

    _list = []

    # 首先提取每个厂商部分
    while 1:
        p = s.find(b"\r\n\r\n")
        if p < 4: break
        _list.append(s[0:p])
        p += 4
        s = s[p:]
    if _list: _list.pop(0)

    results = []

    for s in _list:
        result = __parse_oui_corp(s)
        if not result: continue
        results.append(result)

    return results


results=parse_oui("ixc_syscore/DHCP/data/oui.txt")
print(results)
