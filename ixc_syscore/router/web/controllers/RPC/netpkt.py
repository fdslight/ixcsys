#!/usr/bin/env python3

import ixc_syslib.web.controllers.rpc_controller as rpc

from pywind.global_vars import global_vars


class controller(rpc.controller):
    __runtime = None

    @property
    def router(self):
        return global_vars["ixcsys.router"]

    def rpc_init(self):
        self.__runtime = global_vars["ixcsys.runtime"]

        self.fobjs = {
            "set_fwd_port": self.set_fwd_port,
            "unset_fwd_port": self.unset_fwd_port,
            "get_server_recv_port": self.get_sever_recv_port
        }

    def set_fwd_port(self, flags: int, _id: bytes, fwd_port: int):
        if not isinstance(_id, bytes):
            return 0, (False, "Wrong _id data type")
        if len(_id) != 16:
            return 0, (False, "Wrong _id length")
        try:
            fwd_port = int(fwd_port)
        except ValueError:
            return 0, (False, "Wrong fwd_port data type")

        if fwd_port > 0xfffe or fwd_port < 1:
            return 0, (False, "Wrong fwd_port value")

        pfwd = self.__runtime.get_fwd_instance()
        b = pfwd.set_fwd_port(flags, _id, fwd_port)

        return 0, (b, "")

    def unset_fwd_port(self, flags: int):
        pfwd = self.__runtime.get_fwd_instance()
        pfwd.unset_fwd_port(flags)
        return 0, None

    def get_sever_recv_port(self):
        """获取服务端接收端口
        :return:
        """
        pfwd = self.__runtime.get_fwd_instance()
        port = pfwd.get_server_recv_port()

        return 0, port
