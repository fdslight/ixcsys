#!/usr/bin/env python3

import ixc_syscore.router.pylib.router as router


def send():
    pass


def x():
    pass


r = router.router(send, x)
fd, name = r.netif_create("mydev")

if fd:
    r.netif_delete()

print(fd,name)