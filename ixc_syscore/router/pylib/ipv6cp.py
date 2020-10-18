#!/usr/bin/env python3

import ixc_syscore.router.pylib.ncp as ncp
import ixc_syscore.router.pylib.lcp as lcp

class IPv6CP(ncp.NCP):
    def my_init(self):
        pass

    def parse_options(self, cfg_data: bytes):
        results = []
        if len(cfg_data) < 2: return results
        idx = 0
        while 1:
            try:
                _type = cfg_data[idx]
                length = cfg_data[idx + 1]
            except IndexError:
                results = []
                if self.debug: print("Wrong IPv6CP configure data")
                break
            idx += 2
            e = idx + length
            opt_data = cfg_data[idx:e]
            if len(opt_data) != length:
                results = []
                if self.debug: print("Wrong IPv6CP option length field value")
                break
