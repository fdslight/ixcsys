#!/usr/bin/env python3

fd = open("test.bin", "wb")
fd.write(b"hello")

fd.seek(0)
fd.write(b"world")
fd.close()
