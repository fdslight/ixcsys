#!/bin/sh

cc test_ev.c ../map.c ../timer.c ../ev/ev.c ../ev/ev_select.c ../ev/ev_kqueue.c ../ev/rpc.c -g -Wall
./a.out