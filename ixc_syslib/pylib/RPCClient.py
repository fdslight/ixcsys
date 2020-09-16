#!/usr/bin/env python3
import os, json
import ixc_syslib.pylib.SCGIClient as SCGIClient


class RPCErr(Exception): pass


class RPCClient(SCGIClient.SCGIClient):
    def __init__(self, app_name: str):
        super().__init__("/tmp/ixcsys/%s/scgi.sock" % app_name, is_unix_socket=True)

    def send_request(self, path, body_data: bytes = b"", qs_seq=None):
        """
        :param path: 请求路径
        :param body_data: 请求数据
        :param qs_seq:query string,格式如下[("name1","value1",),("name2","value2",)]
        :return:
        """
        env = {
            "PATH_INFO": "/RPC%s" % path,
            "CONTENT_LENGTH": len(body_data),
        }

        if qs_seq:
            seq = []
            for name, value in qs_seq:
                seq.append("%s=%s" % (name, value,))
            qs_string = "&".join(seq)
        else:
            qs_string = ""

        env["QUERY_STRING"] = qs_string

        user_agent = os.getenv("IXC_MYAPP_NAME")

        if not user_agent:
            env["HTTP_USER_AGENT"] = "RPCClient"
        else:
            env["HTTP_USER_AGENT"] = user_agent

        if not body_data:
            request_method = "GET"
        else:
            request_method = "PUT"

        env["REQUEST_METHOD"] = request_method
        env["REQUEST_URI"] = env["PATH_INFO"] + "?" + env["QUERY_STRING"]

        self.send_scgi_header(env)
        self.send_scgi_body(body_data)

    def handle_response_body(self):
        pass

    def handle_response_finish(self):
        t = self.resp_headers.pop(0)
        _, st = t

        if int(st[0:3]) != 200:
            raise RPCErr("wrong response %s" % st)

        self.sock.close()

    def get_result(self):
        self.handle_response()
        byte_data = self.reader.read()
        s = byte_data.decode("iso-8859-1")

        return json.loads(s)
