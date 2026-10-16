#!/usr/bin/env python3
"""Experimental local transport to the *existing* isolated MOH live-identify runner.

This is a development harness, NOT a libfprint driver or authentication service.
It never opens USB. A caller supplies already converted AND inverted 64x80,
8-bit images. No images or templates are saved by this module.

Protocol (stdin/stdout to this adapter):
 HELLO\n                       -> READY 2\n
 BEGIN 1\n / BEGIN 2\n         -> BEGIN OK\n
 SAMPLE\n + 5120 bytes          -> PROGRESS n 12 | RETRY QUALITY | COMPLETE
 VERIFY\n + 5120 bytes          -> MATCH 1 | MATCH 2 | NO_MATCH | AMBIGUOUS | RETRY QUALITY
 CANCEL\n                      -> CANCELLED (kills engine, clears templates)
 QUIT\n                        -> BYE

SAMPLE is permitted only after BEGIN; verification only after BOTH slots have
completed enrolment. A new BEGIN for an already-completed slot is forbidden.
"""
import argparse
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading

FRAME = 5120
MAX_CMD = 64
MAX_RESPONSE = 256
MAX_ATTEMPTS = 96


class EngineError(Exception):
    pass


class Engine:
    def __init__(self, runner: Path, vendor: Path | None, timeout: float):
        self.runner = runner
        self.vendor = vendor
        self.timeout = timeout
        self.proc = None
        self.events = queue.Queue()
        self.active = None
        self.complete = set()
        self.accepted = {1: 0, 2: 0}
        self.attempts = {1: 0, 2: 0}

    def _reader(self, proc, events):
        try:
            for line in iter(proc.stdout.readline, b''):
                if len(line) > MAX_RESPONSE:
                    events.put('ERROR RESPONSE_TOO_LONG')
                    return
                try:
                    message = line.strip().decode('ascii', 'strict')
                except UnicodeDecodeError:
                    events.put('ERROR NON_ASCII_RESPONSE')
                    return
                if message.startswith(('READY', 'ENROL ', 'IDENTIFY ', 'ERROR ', 'DONE')):
                    events.put(message)
        finally:
            events.put('ERROR ENGINE_EXITED')

    def start(self):
        if self.proc is not None:
            return
        if not self.runner.is_file() or self.runner.is_symlink():
            raise EngineError('RUNNER_NOT_FOUND')
        cmd = ['bash', str(self.runner)]
        if self.vendor is not None:
            cmd.append(str(self.vendor))
        # Runner's own sandbox checks / DLL pinning remain authoritative.
        self.proc = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                     cwd=str(self.runner.parent.parent), bufsize=0)
        # Capture this process's queue: a late reader exit after CANCEL must
        # never inject a stale ENGINE_EXITED into the next engine session.
        events = self.events
        threading.Thread(target=self._reader, args=(self.proc, events), daemon=True).start()
        if self._result() != 'READY':
            self.stop()
            raise EngineError('ENGINE_NOT_READY')

    def _result(self):
        try:
            line = self.events.get(timeout=self.timeout)
        except queue.Empty:
            raise EngineError('ENGINE_TIMEOUT')
        if line == 'READY':
            return line
        if line.startswith('ERROR ') or line == 'DONE':
            raise EngineError('ENGINE_FAILURE')
        return line

    def _send(self, code: bytes, pixels: bytes):
        if self.proc is None or self.proc.poll() is not None:
            raise EngineError('ENGINE_NOT_RUNNING')
        if len(pixels) != FRAME:
            raise EngineError('INVALID_FRAME')
        try:
            self.proc.stdin.write(code + pixels)
            self.proc.stdin.flush()
        except (BrokenPipeError, OSError):
            raise EngineError('ENGINE_PIPE_CLOSED') from None
        return self._result()

    def begin(self, slot):
        if slot not in (1, 2) or slot in self.complete or self.active is not None:
            return 'ERROR BAD_STATE'
        self.start()
        self.active = slot
        return 'BEGIN OK'

    def sample(self, pixels):
        slot = self.active
        if slot is None:
            return 'ERROR BAD_STATE'
        self.attempts[slot] += 1
        if self.attempts[slot] > MAX_ATTEMPTS:
            return 'ERROR ATTEMPT_LIMIT'
        result = self._send(str(slot).encode('ascii'), pixels)
        if result == f'ENROL {slot} ADDED':
            self.accepted[slot] += 1
            if self.accepted[slot] >= 12:
                raise EngineError('INVALID_ENROLL_PROGRESS')
            return f'PROGRESS {self.accepted[slot]} 12'
        if result == f'ENROL {slot} REJECTED':
            return 'RETRY QUALITY'
        if result == f'ENROL {slot} COMPLETE':
            self.accepted[slot] = 12
            self.complete.add(slot)
            self.active = None
            return 'COMPLETE'
        raise EngineError('UNEXPECTED_ENGINE_RESPONSE')

    def verify(self, pixels):
        if self.active is not None or self.complete != {1, 2}:
            return 'ERROR BAD_STATE'
        result = self._send(b'V', pixels)
        return {'IDENTIFY 1': 'MATCH 1', 'IDENTIFY 2': 'MATCH 2',
                'IDENTIFY NONE': 'NO_MATCH',
                'IDENTIFY AMBIGUOUS': 'AMBIGUOUS',
                'IDENTIFY REJECTED': 'RETRY QUALITY'}.get(result, 'ERROR ENGINE_RESPONSE')

    def stop(self):
        proc = self.proc
        self.proc = None
        if proc is not None:
            if proc.poll() is None:
                try:
                    proc.stdin.write(b'Q')
                    proc.stdin.flush()
                except (OSError, ValueError):
                    pass
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.terminate()
                    try:
                        proc.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait()
            if proc.stdin:
                proc.stdin.close()
            if proc.stdout:
                proc.stdout.close()
        self.active = None
        self.complete.clear()
        self.accepted = {1: 0, 2: 0}
        self.attempts = {1: 0, 2: 0}
        self.events = queue.Queue()


def read_frame(stream):
    buf = bytearray(FRAME)
    view = memoryview(buf)
    offset = 0
    while offset < FRAME:
        n = stream.readinto(view[offset:])
        if not n:
            raise EngineError('TRUNCATED_FRAME')
        offset += n
    return buf


def run(runner: Path, vendor: Path | None, timeout: float):
    eng = Engine(runner, vendor, timeout)
    source = sys.stdin.buffer
    try:
        while True:
            raw = source.readline(MAX_CMD + 1)
            if not raw:
                break
            if len(raw) > MAX_CMD or not raw.endswith(b'\n'):
                print('ERROR BAD_COMMAND', flush=True)
                break
            cmd = raw[:-1]
            if cmd == b'HELLO':
                out = 'READY 2'
            elif cmd in (b'BEGIN 1', b'BEGIN 2'):
                out = eng.begin(int(cmd[-1:]))
            elif cmd in (b'SAMPLE', b'VERIFY'):
                # Exactly 5120 bytes of sensitive grayscale input are consumed.
                frame = read_frame(source)
                try:
                    out = eng.sample(frame) if cmd == b'SAMPLE' else eng.verify(frame)
                finally:
                    frame[:] = b'\0' * FRAME
            elif cmd == b'CANCEL':
                eng.stop()
                out = 'CANCELLED'
            elif cmd == b'QUIT':
                eng.stop()
                print('BYE', flush=True)
                return 0
            else:
                out = 'ERROR BAD_COMMAND'
            print(out, flush=True)
    except (EngineError, OSError, ValueError) as exc:
        # Only non-biometric error codes are reported.
        print(f'ERROR {str(exc)}', flush=True)
        return 1
    finally:
        eng.stop()
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runner', type=Path, required=True,
                        help='existing test_moh_isolated_live_identify.sh')
    parser.add_argument('--vendor', type=Path,
                        help='optional pinned private vendor DLL or ZIP; runner defaults to installed DLL')
    parser.add_argument('--timeout', type=float, default=90,
                        help='engine initialisation and response timeout in seconds')
    args = parser.parse_args()
    if not 1 <= args.timeout <= 180:
        parser.error('timeout must be 1..180 seconds')
    raise SystemExit(run(args.runner.resolve(), args.vendor, args.timeout))


if __name__ == '__main__':
    main()
