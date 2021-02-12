#!/usr/bin/env sh

cc tcp_buf.c ../src/tcp_buf.c -o tcp_buf -g -Wall -DDEBUG
./tcp_buf