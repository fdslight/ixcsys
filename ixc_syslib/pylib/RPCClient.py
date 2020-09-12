#!/usr/bin/env python3

import ixc_syslib.pylib.SCGIClient as SCGIClient


class RPCClient(SCGIClient.SCGIClient):
    def send_request(self, url: str):
        pass

    def handle_response_body(self):
        pass

    def handle_response_finish(self):
        byte_data = self.reader.read()
        print(byte_data)

    def get_result(self):
        pass
