#!/bin/sh

cc test_ev.c ../map.c ../timer.c ../ev/ev.c ../ev/ev_select.c
./a.out