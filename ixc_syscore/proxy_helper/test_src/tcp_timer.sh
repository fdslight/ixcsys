#!/usr/bin/env sh

cc tcp_timer.c ../src/tcp_timer.c -o tcp_timer -g -Wall -DDEBUG
./tcp_timer