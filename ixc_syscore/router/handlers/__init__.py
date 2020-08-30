#!/usr/bin/env python3

import pywind.evtframework.handlers.handler as handler


class tapdev(handler.handler):
    def init_func(self, creator_fd, fd: int):
        self.set_fileno(fd)
        self.register(self.fileno)
        self.add_evt_read(self.fileno)

        return self.fileno

    def evt_read(self):
        rs = self.dispatcher.router.netif_rx_data()

        if not rs:
            self.error()
            return
        ''''''

    def evt_write(self):
        rs = self.dispatcher.router.netif_tx_data()
        if not rs:
            self.error()
            return
        ''''''

    def error(self):
        pass

    def delete(self):
        self.unregister(self.fileno)
