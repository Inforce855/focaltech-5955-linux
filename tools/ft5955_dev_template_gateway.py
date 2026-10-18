#!/usr/bin/env python3
"""Local, bounded stdin/stdout bridge for FT5955's audited MOH sandbox.

The native libfprint worker retains exclusive USB ownership. This process
NEVER opens USB, stores biometrics, prints frames, or loads the DLL itself.
Only the child run by ft5955_dev_template_launcher.py loads the pinned DLL inside bwrap.

Wire format:
 MODE E\n                             -> READY 1\n
 MODE V <size> <subfactor>\n<data> -> READY 1\n
 FRAME\n<5120 bytes>                -> PROGRESS n 12 | RETRY QUALITY |
                                         MATCH | NO_MATCH | COMPLETE;
 on COMPLETE followed by TEMPLATE <size> <subfactor>\n<bytes>
 QUIT\n                             -> BYE\n
DEV ONLY: actual matching output, never approval for PAM authentication.
"""
from __future__ import annotations
import argparse
import os
from pathlib import Path
import select
import signal
import struct
import subprocess
import sys
import time

FRAME = 5120
MAX_TEMPLATE = 1 << 20
TIMEOUT = 180
ENGINE_DIR = Path(__file__).resolve().parent


def wipe(b: bytearray) -> None:
    b[:] = b'\0' * len(b)


class Engine:
    def __init__(self, command: list[str]):
        self.cmd, self.proc = command, None

    def read_exact(self, length: int) -> bytearray:
        if self.proc is None or not self.proc.stdout:
            raise RuntimeError('MOH engine not running')
        data = bytearray()
        end = time.monotonic() + TIMEOUT
        fd = self.proc.stdout.fileno()
        while len(data) < length:
            remain = end - time.monotonic()
            if remain <= 0 or not select.select([fd], [], [], remain)[0]:
                raise RuntimeError('MOH engine response timeout')
            piece = os.read(fd, min(65536, length - len(data)))
            if not piece:
                raise RuntimeError('MOH engine closed its pipe')
            data.extend(piece)
        return data

    def line(self) -> str:
        data = bytearray()
        for _ in range(256):
            b = self.read_exact(1)[0]
            if b == 10:
                return data.decode('ascii', 'strict')
            if not 32 <= b <= 126:
                raise RuntimeError('Invalid MOH protocol character')
            data.append(b)
        raise RuntimeError('Oversized MOH protocol line')

    def send(self, data: bytes | bytearray | memoryview) -> None:
        if not self.proc or not self.proc.stdin:
            raise RuntimeError('Engine not running')
        self.proc.stdin.write(data)
        self.proc.stdin.flush()

    def start(self) -> None:
        self.proc = subprocess.Popen(self.cmd, stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                     bufsize=0, cwd=ENGINE_DIR, start_new_session=True)
        for _ in range(32):
            line = self.line()
            if line == 'READY':
                return
            if line.startswith('ERROR '):
                raise RuntimeError('MOH engine refused startup')
        raise RuntimeError('MOH runner did not report READY')

    def frame(self, mode: str, image: bytearray) -> str:
        self.send((b'E' if mode == 'E' else b'V') + image)
        response = self.line()
        if response.startswith('ERROR ') or response not in (
                'RETRY QUALITY', 'COMPLETE', 'MATCH', 'NO_MATCH',
                *(f'PROGRESS {i} 12' for i in range(1, 12))):
            raise RuntimeError('MOH refused sample or returned unknown result')
        return response

    def exported(self) -> tuple[bytearray, int]:
        self.send(b'X')
        fields = self.line().split()
        if len(fields) != 3 or fields[0] != 'TEMPLATE' or not all(x.isascii() and x.isdecimal() for x in fields[1:]):
            raise RuntimeError('MOH did not export a valid template')
        n, subfactor = int(fields[1]), int(fields[2])
        if not (1 <= n <= MAX_TEMPLATE and 0 <= subfactor <= 255):
            raise RuntimeError('MOH template bounds violation')
        return self.read_exact(n), subfactor

    def imported(self, template: bytearray, subfactor: int) -> None:
        if not 1 <= len(template) <= MAX_TEMPLATE or not 0 <= subfactor <= 255:
            raise ValueError('Invalid template')
        self.send(b'I' + struct.pack('<IB', len(template), subfactor) + template)
        if self.line() != 'IMPORTED':
            raise RuntimeError('MOH refused template import')

    def close(self) -> None:
        proc, self.proc = self.proc, None
        if proc is None:
            return
        if proc.poll() is None:
            try:
                if proc.stdin:
                    proc.stdin.write(b'Q')
                    proc.stdin.flush()
            except (OSError, ValueError, BrokenPipeError):
                pass
        if proc.stdin: proc.stdin.close()
        try:
            proc.wait(timeout=4)
        except subprocess.TimeoutExpired:
            # The audited runner may have spawned timeout/bwrap descendants.
            # All were started in a private process group for bounded teardown.
            try: os.killpg(proc.pid, signal.SIGTERM)
            except ProcessLookupError: pass
            try: proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                try: os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError: pass
                proc.wait()
        if proc.stdout: proc.stdout.close()


def stdin_line() -> str:
    raw = sys.stdin.buffer.readline(128)
    if not raw or len(raw) > 127 or not raw.endswith(b'\n'):
        raise RuntimeError('Bad or missing IPC command')
    return raw[:-1].decode('ascii', 'strict')


def stdin_exact(n: int) -> bytearray:
    data = bytearray()
    while len(data) < n:
        p = sys.stdin.buffer.read(n - len(data))
        if not p: raise RuntimeError('Truncated IPC frame')
        data.extend(p)
    return data


def line_out(line: str) -> None:
    sys.stdout.buffer.write(line.encode('ascii')+b'\n')
    sys.stdout.buffer.flush()


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument('--moh-dir',type=Path,default=Path.home()/'Projects/focaltech-5955-moh-test')
    args = p.parse_args()
    if os.geteuid() == 0:
        raise RuntimeError('Refusing to run vendor MOH sandbox supervisor as root')
    if args.moh_dir != Path('/opt/ft5955-dev'):
        raise RuntimeError('Dedicated service requires fixed protected MOH directory')
    if not (args.moh_dir/'live-template').is_file():
        raise RuntimeError('Missing protected template engine executable')
    # The copy of template_runner.py substitutes only the C probe, retaining
    # the original runner's SHA-256 and isolated execution checks.
    engine = Engine([sys.executable, str(ENGINE_DIR/'ft5955_dev_template_launcher.py')])
    initialized = False
    mode = ''
    # On parent cancellation/termination, execute the same sandbox cleanup.
    def terminate(signum, frame):
        raise SystemExit(128 + signum)
    signal.signal(signal.SIGTERM, terminate)
    try:
        engine.start()
        while True:
            command = stdin_line()
            if command == 'QUIT':
                line_out('BYE'); break
            if command == 'MODE E' and not initialized:
                mode='E'; initialized=True;line_out('READY 1')
            elif command.startswith('MODE V ') and not initialized:
                fields=command.split()
                if len(fields)!=4 or not all(x.isdecimal() for x in fields[2:]):
                    raise RuntimeError('Invalid verify mode header')
                n,subfactor=int(fields[2]),int(fields[3])
                if not 1<=n<=MAX_TEMPLATE or not 0<=subfactor<=255:
                    raise RuntimeError('Template size or subfactor invalid')
                template=stdin_exact(n)
                try: engine.imported(template,subfactor)
                finally: wipe(template)
                mode='V';initialized=True;line_out('READY 1')
            elif command=='FRAME' and initialized:
                frame=stdin_exact(FRAME)
                try: response=engine.frame(mode,frame)
                finally: wipe(frame)
                line_out(response)
                if response == 'COMPLETE':
                    blob, subfactor=engine.exported()
                    try:
                        line_out(f'TEMPLATE {len(blob)} {subfactor}')
                        sys.stdout.buffer.write(blob)
                        sys.stdout.buffer.flush()
                    finally: wipe(blob)
            else:
                raise RuntimeError('IPC state violation')
        return 0
    finally:
        engine.close()

if __name__=='__main__':
    try:
        raise SystemExit(main())
    except (OSError,ValueError,RuntimeError) as exc:
        # Do not include biometric data in errors or logs.
        print(f'FT5955 MOH IPC stopped: {type(exc).__name__}',file=sys.stderr)
        raise SystemExit(3)
