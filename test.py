#!/usr/bin/env python3
import ixc_syslib.pylib.RPCClient as RPCClient

client = RPCClient.RPCClient("/tmp/ixcsys/syscall/scgi.sock", is_unix_socket=True)

env = {
    "CONTENT_LENGTH": 0,
    "REQUEST_URI": "/",
    "PATH_INFO": "/",
    "HTTP_USER_AGENT": "SCGIClient",
    "REQUEST_METHOD": "GET"
}
client.send_scgi_header(env)
client.send_scgi_body(b"")
client.handle_response()
