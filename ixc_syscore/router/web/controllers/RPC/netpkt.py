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

    def set_fwd_port(self, is_link_data: bool, flags: int, fwd_port: int):
        pfwd = self.__runtime.get_fwd_instance()
        return (0, pfwd.set_fwd_port(is_link_data, flags, fwd_port),)

    def unset_fwd_port(self, is_link_data: bool, flags: int):
        pfwd = self.__runtime.get_fwd_instance()
        return (0, pfwd.unset_fwd_port(is_link_data, flags),)

    def get_sever_recv_port(self):
        """获取服务端接收端口
        :return:
        """
        pfwd = self.__runtime.get_fwd_instance()

        return (0, pfwd.get_server_recv_port(),)
