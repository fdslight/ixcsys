#!/usr/bin/env python3

import ixc_syscore.proxy.pylib.simple_qos as simple_qos
import ixc_syslib.pylib.ev_handlers.nspkt as nspkt


class netpkt_handler(nspkt.nspkt_handler):
    __qos = None

    def my_init(self, *args, **kwargs):
        self.__qos = simple_qos.qos(simple_qos.QTYPE_DST)

    def handle_recv(self, if_type: int, ipproto: int, flags: int, message: bytes):
        if ipproto not in (1, 6, 17, 44, 58,): return
        self.__qos.add_to_queue(message)
        self.add_to_loop_task(self.fileno)

    def handle_data_from_local_net(self):
        results = self.__qos.get_queue()

        for message in results:
            self.dispatcher.handle_msg_from_local(message)

        if not results:
            self.del_loop_task(self.fileno)
        else:
            self.add_to_loop_task(self.fileno)

    def task_loop(self):
        self.handle_data_from_local_net()
