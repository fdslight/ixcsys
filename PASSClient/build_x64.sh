#!/usr/bin/env bash
dotnet publish -r linux-x64 -c Release

gcc linux_tap.c -shared -fPIC -o liblinux_tap.so



