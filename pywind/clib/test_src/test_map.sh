#!/bin/sh

cc test_map.c ../map.c ../debug.c -g -Wall -DDEBUG
./a.out
