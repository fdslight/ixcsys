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

import multiprocessing, time


def func():
    time.sleep(5)
    print("hello")


if __name__=="__main__":
    p = multiprocessing.Process(target=func,args=())
    p.start()
    p.join()

