#!/usr/bin/env python3
import os

fd=os.popen("ifconfig bridge create")
s=fd.read()
fd.close()

print(s.encode())

os.system("ifconfig bridge0 destroy")