#!/bin/env python3
# Simple ping implementation
import sys

print('0')
sys.stdout.flush()

for l in sys.stdin:
    reqid, mtype, data = l.split(':')
    print('{}:{}'.format(reqid, data[:-1]))
    sys.stdout.flush()

