#!/usr/bin/env python3

import pywind.evtframework.handlers.handler as handler


class tundevice(handler.handler):
    def init_func(self, creator_fd, fd):
        self.set_fileno(fd)
        self.register(self.fileno)
        self.add_evt_read(self.fileno)

        return self.fileno

    def evt_read(self):
        r = self.dispatcher.router.tundev_rx_data()
        if not r: self.error()

    def evt_write(self):
        r = self.dispatcher.router.tundev_tx_data()
        if not r: self.error()

    def error(self):
        self.delete_handler(self.fileno)

    def delete(self):
        self.unregister(self.fileno)
