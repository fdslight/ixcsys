#!/usr/bin/env python3

import pywind.evtframework.handlers.handler as handler


class tundevice(handler.handler):
    def init_func(self, creator_fd, fd):
        self.set_fileno(fd)
        self.register(self.fileno)
        self.add_evt_read(self.fileno)

        return self.fileno

    def evt_read(self):
        pass

    def evt_write(self):
        pass

    def error(self):
        self.delete_handler(self.fileno)

    def delete(self):
        self.unregister(self.fileno)
