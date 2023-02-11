#!/usr/bin/env python3

class helper(object):
    __debug = None

    def __init__(self, debug):
        self.__debug = debug
        print("this is python3", debug)

    def handle_data(self, byte_data: bytes):
        print(byte_data)
