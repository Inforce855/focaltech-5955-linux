#!/usr/bin/env python3
"""Synthetic stream only; never opens USB. Eight dummy 10240-byte frames."""
import sys
count = int(sys.argv[1]) if len(sys.argv)>1 else 8
assert 1 <= count <= 8
for _ in range(count):
    b=b'F'+(10240).to_bytes(2,'big')+bytes(10240)
    sys.stdout.buffer.write(b)
    sys.stdout.buffer.flush()
sys.stdout.buffer.write(b'D\x00\x04DONE')
sys.stdout.buffer.flush()
