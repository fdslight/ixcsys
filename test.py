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


def parse_ieee_ma_info(path: str):
    """解析IEEE MA的厂商MAC地址分配信息
    """
    fdst = open(path, "rb")
    first_line = True
    results = {}
    for line in fdst:
        if first_line:
            first_line = False
            continue
        s = line.decode()
        s = s.replace("\r\n", "")
        _list = s.split(",")
        if len(_list) != 4: continue
        name = _list[1]
        results[name] = _list[2]

    return results


results = parse_ieee_ma_info("ixc_syscore/DHCP/data/oui.csv")
print(results)
