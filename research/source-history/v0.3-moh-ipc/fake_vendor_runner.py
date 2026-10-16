#!/usr/bin/env python3
"""Synthetic-only stand-in for the vendor runner; no biometric identification."""
import sys

sys.stdout.write('READY\n')
sys.stdout.flush()
counts = [0, 0]
while True:
    command = sys.stdin.buffer.read(1)
    if not command or command == b'Q':
        break
    data = sys.stdin.buffer.read(5120)
    if len(data) != 5120:
        print('ERROR truncated', flush=True)
        break
    if command in (b'1', b'2'):
        index = int(command) - 1
        if data[0] == 0:
            print(f'ENROL {index+1} REJECTED', flush=True)
        else:
            counts[index] += 1
            print(f'ENROL {index+1} '+('COMPLETE' if counts[index] == 12 else 'ADDED'), flush=True)
    elif command == b'V':
        label = {1: '1', 2: '2', 3: 'NONE', 4: 'AMBIGUOUS', 0: 'REJECTED'}.get(data[0], 'NONE')
        print('IDENTIFY '+label, flush=True)
    else:
        print('ERROR command', flush=True)
        break
print('DONE', flush=True)
