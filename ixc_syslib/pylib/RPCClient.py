#!/usr/bin/env python3
import os, pickle
import ixc_syslib.pylib.SCGIClient as SCGIClient


class RPCErr(Exception): pass


class RPCMethodNotFound(RPCErr): pass


class RPCArgErr(RPCErr): pass


class RPCProtoErr(RPCErr): pass


class RPCSysErr(RPCErr): pass


# 未发生故障
ERR_NO = 0
# 没有找到方法
ERR_NOT_FOUND_METHOD = -1
# 参数故障
ERR_ARGS = -2
#  协议故障
ERR_PROTO = -3
# 系统发生故障
ERR_SYS = -4


class RPCClient(SCGIClient.SCGIClient):
    def __init__(self, app_name: str):
        super().__init__("/tmp/ixcsys/%s/scgi.sock" % app_name, is_unix_socket=True)

    def send_request(self, path, body_data: bytes):
        """
        :param path: 请求路径
        :param body_data: 请求数据
        :param qs_seq:query string,格式如下[("name1","value1",),("name2","value2",)]
        :return:
        """
        env = {"PATH_INFO": "/RPC%s" % path, "CONTENT_LENGTH": len(body_data), "QUERY_STRING": ""}

        user_agent = os.getenv("IXC_MYAPP_NAME")

        if not user_agent:
            env["HTTP_USER_AGENT"] = "RPCClient"
        else:
            env["HTTP_USER_AGENT"] = user_agent

        env["REQUEST_METHOD"] = "PUT"
        env["REQUEST_URI"] = env["PATH_INFO"] + "?" + env["QUERY_STRING"]
        env["HTTP_X_IXCSYS_RPC"] = 1
        env["CONTENT_TYPE"] = "application/octet-stream"

        self.send_scgi_header(env)
        self.send_scgi_body(body_data)

    def send_rpc_request(self, path, fname: str, *args, **kwargs):
        o = {
            "name": fname,
            "args": args,
            "kwargs": kwargs
        }
        self.send_request(path, pickle.dumps(o))

    def handle_response_finish(self):
        t = self.resp_headers.pop(0)
        _, st = t

        if int(st[0:3]) != 200:
            raise RPCErr("wrong response %s" % st)

        self.sock.close()

    def get_result(self):
        self.handle_response()
        byte_data = self.reader.read()

        result = pickle.loads(byte_data)
        is_err = result["is_error"]
        message = result["message"]

        if is_err == ERR_NOT_FOUND_METHOD:
            raise RPCMethodNotFound(message)
        if is_err == ERR_ARGS:
            raise RPCArgErr(message)
        if is_err == ERR_PROTO:
            raise RPCProtoErr(message)
        if is_err == ERR_SYS:
            raise RPCSysErr(message)

        return (is_err, message,)


def fn_call(app_name: str, path: str, fn_name: str, *args, **kwargs):
    is_error, message = fn_call_with_error(app_name, path, fn_name, *args, **kwargs)

    if is_error: raise RPCErr(message)

    return message


def fn_call_with_error(app_name: str, path: str, fn_name: str, *args, **kwargs):
    """此函数调用的时候返回带error标志,用以说明是否发生故障
    :param app_name:
    :param path:
    :param fn_name:
    :param args:
    :param kwargs:
    :return:
    """
    cls = RPCClient(app_name)
    cls.send_rpc_request(path, fn_name, *args, **kwargs)

    result = cls.get_result()

    return result
