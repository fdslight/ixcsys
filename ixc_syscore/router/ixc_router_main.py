#!/usr/bin/env python3

import pywind.evtframework.evt_dispatcher as dispatcher

import ixc_syscore.router.pylib.router as router


class service(dispatcher.dispatcher):
    __router = None

    def _write_ev_tell(self, fd: int, flags: int):
        pass

    def _recv_from_proto_stack(self, byte_data: bytes, flags: int):
        """从协议栈接收消息
        """

    def send_to_proto_stack(self, byte_data: bytes, flags: int):
        """向协议栈发送消息
        """
        self.__router.send_netpkt(byte_data,flags)

    def init_func(self, *args, **kwargs):
        self.__router = router.router(self._recv_from_proto_stack, self._write_ev_tell)

    def myloop(self):
        pass



