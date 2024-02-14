#!/bin/sh

cc test_fuzzyMap.c ../fuzzyMap.c ../debug.c -g -Wall -DDEBUG
./a.out