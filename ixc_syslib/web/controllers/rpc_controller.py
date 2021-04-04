#!/usr/bin/env python3
import pickle
import pywind.web.appframework.app_handler as app_handler
import ixc_syslib.pylib.RPCClient as RPCClient
import ixc_syslib.pylib.logging as logging


class controller(app_handler.handler):
    fobjs = None

    def initialize(self):
        self.fobjs = {}
        self.request.set_allow_methods(["PUT"])

        try:
            enable_rpc = self.request.environ.get("HTTP_X_IXCSYS_RPC", 0)
        except ValueError:
            return False

        return bool(enable_rpc)

    def send_rpc_response(self, is_err: int, response_data):
        o = {
            "is_error": is_err,
            "message": response_data
        }
        byte_data = pickle.dumps(o)
        self.finish_with_bytes(
            "application/octet-stream", byte_data
        )

    def handle_rpc_request(self, fname: str, *args, **kwargs):
        fn = self.fobjs[fname]
        try:
            is_err, message = fn(*args, **kwargs)
        except NameError:
            self.send_rpc_response(RPCClient.ERR_NOT_FOUND_METHOD, "not found RPC function %s" % fname)
            return
        except TypeError:
            logging.print_error()
            self.send_rpc_response(RPCClient.ERR_ARGS, "Wrong argument or return value for function %s" % fname)
            return
        except:
            logging.print_error()
            self.send_rpc_response(RPCClient.ERR_SYS, "system error for RPC request %s" % fname)
            return

        self.send_rpc_response(is_err, message)

    def handle(self):
        raw_data = self.request.get_raw_body()
        rpc_request = pickle.loads(raw_data)

        if not isinstance(rpc_request, dict):
            self.send_rpc_response(RPCClient.ERR_PROTO, "wrong request data %s" % rpc_request)
            return

        try:
            fname = rpc_request["name"]
            args = rpc_request["args"]
            kwargs = rpc_request["kwargs"]
        except KeyError:
            self.send_rpc_response(RPCClient.ERR_PROTO, "wrong request data %s" % rpc_request)
            return

        self.rpc_init()

        # 检查函数对象集合是否是字典对象
        if not isinstance(self.fobjs, dict):
            self.send_rpc_response(RPCClient.ERR_PROTO, "function object set must be dict object %s")
            return

        if fname not in self.fobjs:
            self.send_rpc_response(RPCClient.ERR_NOT_FOUND_METHOD, "not found RPC function %s" % fname)
            return
        self.handle_rpc_request(fname, *args, **kwargs)

    def rpc_init(self):
        """RPC初始化函数,该函数用于注册函数目的
        :return:
        """
        pass
