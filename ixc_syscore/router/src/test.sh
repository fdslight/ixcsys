#!/bin/sh

cc ./main.c ../../../pywind/clib/pfile.c -I /opt/python39/include/python3.9 -L/opt/python39/lib -lpython3.9 -DDEBUG -o ../ixc_router_core
