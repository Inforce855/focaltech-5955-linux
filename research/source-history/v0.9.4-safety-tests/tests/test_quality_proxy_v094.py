#!/usr/bin/env python3
"""Offline wire-protocol tests. Uses synthetic frames and a fake gateway only."""
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import textwrap

PROXY = Path(__file__).with_name('ft5955_quality_proxy_v094.py')
MOCK = '''\
import sys
s = sys.stdin.buffer
out = sys.stdout.buffer
command = s.readline()
if command.startswith(b'MODE V '):
    size = int(command.split()[2]); template = s.read(size)
    assert template == b'ab'
    out.write(b'READY 1\\n'); out.flush()
    assert s.readline() == b'FRAME\\n'
    frame = s.read(5120)
    assert frame == bytes([2]) * 5120, 'first frame must be discarded'
    out.write(b'MATCH\\n'); out.flush()
elif command == b'MODE E\\n':
    out.write(b'READY 1\\n'); out.flush()
    assert s.readline() == b'FRAME\\n'
    assert s.read(5120) == bytes([3]) * 5120
    out.write(b'PROGRESS 1 12\\n'); out.flush()
else:
    raise AssertionError('Unexpected mode')
assert s.readline() == b'QUIT\\n'
out.write(b'BYE\\n'); out.flush()
'''


def exercise(payload, expected, environment):
    p = subprocess.run([sys.executable, str(PROXY)], input=payload,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       env=environment, timeout=12, check=False)
    if p.returncode or p.stdout != expected:
        raise AssertionError((p.returncode, p.stdout, p.stderr))


def main():
    with tempfile.TemporaryDirectory() as d:
        target = Path(d) / 'engine_gateway.py'
        target.write_text(MOCK)
        env = dict(os.environ, FT5955_QUALITY_PROBE_ENABLE='1',
                   FT5955_ORIGINAL_ENGINE_GATEWAY=str(target))
        exercise(b'MODE V 2 0\nabFRAME\n' + bytes([1])*5120 +
                 b'FRAME\n' + bytes([2])*5120 + b'QUIT\n',
                 b'READY 1\nRETRY QUALITY\nMATCH\nBYE\n', env)
        exercise(b'MODE E\nFRAME\n' + bytes([3])*5120 + b'QUIT\n',
                 b'READY 1\nPROGRESS 1 12\nBYE\n', env)
        bad = dict(env, FT5955_QUALITY_PROBE_ENABLE='0')
        p = subprocess.run([sys.executable, str(PROXY)], input=b'',
                           capture_output=True, env=bad, timeout=12)
        assert p.returncode != 0 and not p.stdout
    print('PASS: offline injected verify retry, subsequent real frame, unmodified enrol path, opt-in refusal')


if __name__ == '__main__':
    main()
