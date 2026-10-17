#!/usr/bin/env python3
"""Experimental RAM-only restart test for the existing FT5955 MOH engine.

Enroll 12 accepted touches, export the temporary template through a LOCAL
anonymous pipe, DESTROY the engine sandbox, create a fresh one, import that
same template and verify fresh touches. Nothing is saved to disk; do not use
for system authentication. Explicit --live is required for hardware access.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import select
import struct
import subprocess
import sys
import time

from live_capture_client import capture_batch, prompt, MAX_BATCHES, MAX_FRAMES

HERE = Path(__file__).resolve().parent
DEFAULT_MOH = Path.home() / 'Projects/focaltech-5955-moh-test'
MAX_TEMPLATE = 1 << 20
MAX_LINE = 256

class PrivateEngine:
    def __init__(self, command: list[str], timeout=120):
        self.command = command
        self.timeout = timeout
        self.proc = None

    def start(self):
        if self.proc is not None:
            raise RuntimeError('Engine already started')
        self.proc = subprocess.Popen(self.command, stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                     bufsize=0, cwd=HERE)
        # The original audited shell runner prints brief non-biometric build/
        # launch messages BEFORE the sandboxed engine reports READY.
        for _ in range(32):
            reply = self._line()
            if reply == 'READY':
                return
            if reply.startswith('ERROR '):
                raise RuntimeError('Engine preparation failed: ' + reply)
        raise RuntimeError('Engine did not report READY')

    def _read(self, n: int) -> bytearray:
        if self.proc is None or self.proc.stdout is None:
            raise RuntimeError('Engine unavailable')
        fd = self.proc.stdout.fileno()
        data = bytearray()
        limit = time.monotonic() + self.timeout
        while len(data) < n:
            remaining = limit - time.monotonic()
            if remaining <= 0 or not select.select([fd], [], [], remaining)[0]:
                raise RuntimeError('Engine response timed out')
            block = os.read(fd, min(65536, n - len(data)))
            if not block:
                raise RuntimeError('Engine disconnected')
            data.extend(block)
        return data

    def _line(self) -> str:
        out = bytearray()
        while len(out) < MAX_LINE:
            ch = self._read(1)
            if ch == b'\n':
                return out.decode('ascii', 'strict')
            if ch[0] < 32 or ch[0] > 126:
                raise RuntimeError('Invalid text in engine protocol')
            out.extend(ch)
        raise RuntimeError('Engine response exceeded limit')

    def _write(self, message: bytes):
        if not self.proc or self.proc.poll() is not None or not self.proc.stdin:
            raise RuntimeError('Engine unavailable')
        self.proc.stdin.write(message)
        self.proc.stdin.flush()

    def ask(self, operation: str, pixels: bytes | None = None) -> str:
        if operation not in ('SAMPLE', 'VERIFY') or pixels is None or len(pixels) != 5120:
            raise ValueError('Invalid operation or converted fingerprint size')
        self._write((b'E' if operation == 'SAMPLE' else b'V') + pixels)
        reply = self._line()
        if reply.startswith('ERROR '):
            raise RuntimeError('MOH: ' + reply)
        # The existing v0.3 UI labels this one-template test as finger 1.
        if reply == 'MATCH':
            return 'MATCH 1'
        return reply

    def export_template(self) -> bytearray:
        self._write(b'X')
        response = self._line().split()
        if (len(response) != 3 or response[0] != 'TEMPLATE' or
                not response[1].isdigit() or not response[2].isdigit()):
            raise RuntimeError('Invalid export header')
        n, subfactor = int(response[1]), int(response[2])
        if not 1 <= n <= MAX_TEMPLATE or not 0 <= subfactor <= 255:
            raise RuntimeError('Invalid exported template geometry')
        result = bytearray(struct.pack('<IB', n, subfactor))
        result.extend(self._read(n))
        return result

    def import_template(self, private_template: bytearray):
        if len(private_template) < 6:
            raise ValueError('Invalid template buffer')
        n = struct.unpack_from('<I', private_template)[0]
        if not 1 <= n <= MAX_TEMPLATE or n + 5 != len(private_template):
            raise ValueError('Invalid template length')
        # Avoid producing an additional immutable bytes copy of the template.
        self._write(b'I')
        if not self.proc or not self.proc.stdin:
            raise RuntimeError('Engine unavailable')
        self.proc.stdin.write(memoryview(private_template))
        self.proc.stdin.flush()
        if self._line() != 'IMPORTED':
            raise RuntimeError('Template import rejected')

    def close(self):
        proc = self.proc
        self.proc = None
        if not proc:
            return
        if proc.poll() is None and proc.stdin:
            try:
                proc.stdin.write(b'Q')
                proc.stdin.flush()
            except (OSError, ValueError):
                pass
        if proc.stdin and not proc.stdin.closed:
            proc.stdin.close()
        try:
            proc.wait(timeout=8)
        except subprocess.TimeoutExpired:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
        if proc.stdout:
            proc.stdout.close()


def wipe(value: bytearray):
    value[:] = b'\x00' * len(value)


def live_main(moh_dir: Path):
    if os.geteuid() == 0:
        raise RuntimeError('Run as normal user, not root')
    tools = moh_dir / 'tools'
    helper_file = tools / 'auto_contact_capture.py'
    if not helper_file.is_file() or helper_file.is_symlink():
        raise RuntimeError('Expected original MOH capture helper is missing')
    if subprocess.run(['sudo', '-n', 'true'], stdout=subprocess.DEVNULL,
                      stderr=subprocess.DEVNULL).returncode:
        raise RuntimeError('Run sudo -v to authorise the existing bounded helper')
    sys.path.insert(0, str(tools))
    from live_finger_identify import prepared_pixels
    command = [sys.executable, str(HERE / 'template_runner.py')]
    helper = ['sudo', '-n', sys.executable, str(helper_file)]
    engine = PrivateEngine(command)
    template = None
    print('FT5955 isolated MOH template restart experiment (one finger, RAM only).')
    print('This will NOT enrol Linux login or save a template.')
    print('First, enrol one finger with 12 accepted touches, then verify after restarting the engine.')
    print('Finger must be lifted completely between scans; q quits.')
    try:
        engine.start()
        total, done = 0, False
        for batch in range(MAX_BATCHES):
            prompt(f'Enrol finger: Enter starts bounded batch {batch+1}; q quits: ')
            done, count, rejected = capture_batch(engine, 'SAMPLE', helper, prepared_pixels)
            total += count
            if done: break
            print(f'  Batch ended: {count} impressions, {rejected} rejected.')
            if total >= MAX_FRAMES: break
        if not done:
            raise RuntimeError('Enrolment did not complete within bounded budget')
        template = engine.export_template()
        print('Template exported privately to supervisor memory (not saved).')
        engine.close()
        print('Original engine sandbox closed. Starting a fresh engine sandbox...')
        engine = PrivateEngine(command)
        engine.start()
        engine.import_template(template)
        wipe(template)
        template = None
        print('Template restored in the NEW engine process; original copy cleared.')
        print('Test the enrolled finger, then test another finger for NO_MATCH.')
        while True:
            prompt('Verify after engine restart: Enter starts one scan; q quits: ')
            done, count, _ = capture_batch(engine, 'VERIFY', helper, prepared_pixels,
                                           first_only=True)
            if not count:
                print('  No fresh touch captured.')
    except (KeyboardInterrupt, EOFError):
        print('Session cancelled; all temporary template copies discarded.')
        return 0
    finally:
        if template is not None:
            wipe(template)
        engine.close()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--live', action='store_true', help='explicit real USB test')
    p.add_argument('--moh-dir', type=Path, default=DEFAULT_MOH)
    args = p.parse_args()
    if not args.live:
        p.error('Pass --live explicitly to use the physical fingerprint reader')
    try:
        return live_main(args.moh_dir.resolve())
    except (OSError, RuntimeError, ValueError) as exc:
        print('STOPPED: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
