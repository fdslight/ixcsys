#!/usr/bin/env sh

ip -6 addr add 8888::2/64 dev ixclanbr

ping -6 8888::1