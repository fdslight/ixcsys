#!/usr/bin/env python3

import random

seq = []

for x in range(100):
    a = 1
    b = 7
    c = random.randint(124, 50000)
    seq.append(
        (a << 24) | (7 << 16) | c
    )

results = []
for x in seq:
    results.append(x % 1024)

print(results)