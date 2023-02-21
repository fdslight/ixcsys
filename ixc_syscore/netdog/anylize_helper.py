#!/usr/bin/env python3

import netpkt_anylize


class helper(object):
    __npkt_anylize = None
    __debug = None

    def __init__(self, debug: bool):
        self.__debug = debug
        self.__npkt_anylize = netpkt_anylize.npkt_anylize()

    def start(self):
        print(self.__npkt_anylize.worker_no_get())

    def release(self):
        pass
