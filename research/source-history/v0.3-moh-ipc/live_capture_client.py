#!/usr/bin/env python3
"""EXPERIMENTAL real sensor -> IPC -> sandboxed MOH, memory only.

This is a diagnostic demonstration, NOT a libfprint/fprintd driver.
No templates persist, no login changes, no data files. Requires --live.
The USB helper/processing code is *imported from* the known-good MOH checkout;
we do not copy/reimplement the image conversion or USB protocol.
"""
from __future__ import annotations
import argparse
import os
from pathlib import Path
import subprocess
import select
import time
import sys
from typing import Callable

ROOT = Path(__file__).resolve().parent
FRAME = 5120
RAW = 10240
MAX_MSG = 600
MAX_BATCHES = 16
MAX_FRAMES = 96


def exact(stream, n: int) -> bytes:
    out = bytearray()
    while len(out) < n:
        piece = stream.read(n - len(out))
        if not piece:
            raise EOFError("Sensor helper ended in the middle of a record")
        out.extend(piece)
    return bytes(out)


def read_record(stream):
    kind = stream.read(1)
    if kind == b'':
        return None
    if kind not in (b'F', b'S', b'E', b'D'):
        raise RuntimeError('Invalid helper record kind')
    count = int.from_bytes(exact(stream, 2), 'big')
    if (kind == b'F' and count != RAW) or (kind != b'F' and count > MAX_MSG):
        raise RuntimeError('Invalid helper record size')
    return kind, exact(stream, count)


class AdapterClient:
    def __init__(self, command: list[str], timeout: int = 90):
        self.command = command
        self.timeout = timeout
        self.proc: subprocess.Popen | None = None

    def start(self):
        if self.proc is not None:
            raise RuntimeError('Adapter already running')
        self.proc = subprocess.Popen(self.command, cwd=ROOT,
                                     stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.DEVNULL, bufsize=0)
        if self.ask('HELLO') != 'READY 2':
            raise RuntimeError('Adapter handshake failed')

    def ask(self, command: str, pixels: bytes | None = None) -> str:
        proc = self.proc
        if proc is None or proc.poll() is not None or proc.stdin is None or proc.stdout is None:
            raise RuntimeError('Adapter unavailable')
        if pixels is not None and len(pixels) != FRAME:
            raise ValueError('Invalid greyscale length')
        proc.stdin.write(command.encode('ascii') + b'\n')
        if pixels is not None:
            proc.stdin.write(pixels)
        proc.stdin.flush()
        # stdout is restricted to one bounded line per request. In this
        # single-user diagnostic no concurrent requests are permitted.
        fd = proc.stdout.fileno()
        deadline = time.monotonic() + self.timeout
        response = bytearray()
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise RuntimeError('MOH adapter timed out')
            readable, _, _ = select.select([fd], [], [], remaining)
            if not readable:
                raise RuntimeError('MOH adapter timed out')
            one = os.read(fd, 1)
            if not one:
                raise RuntimeError('MOH adapter exited without a response')
            response.extend(one)
            if len(response) > 128:
                raise RuntimeError('MOH adapter response too long')
            if one == b'\n':
                break
        result = response.strip().decode('ascii', 'strict')
        if result.startswith('ERROR '):
            raise RuntimeError('Adapter: ' + result)
        return result

    def close(self):
        proc = self.proc
        self.proc = None
        if proc is None:
            return
        if proc.poll() is None and proc.stdin:
            try:
                proc.stdin.write(b'QUIT\n')
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


def capture_batch(client: AdapterClient, operation: str,
                  helper: list[str], prepare: Callable[[bytes], bytes],
                  *, first_only: bool = False) -> tuple[bool, int, int]:
    """(operation completed, number transmitted, rejected); at most 8 frames.

    The original privileged helper itself enforces 8 frames / 240 polls.
    No biometric data is printed or saved here.
    """
    if operation not in ('SAMPLE', 'VERIFY'):
        raise ValueError('Invalid capture operation')
    proc = subprocess.Popen(helper, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL, bufsize=0)
    sent = 0
    retries = 0
    complete = False
    try:
        while True:
            record = read_record(proc.stdout)
            if record is None:
                break
            kind, payload = record
            if kind == b'F':
                pixels = prepare(payload)
                if not isinstance(pixels, bytes) or len(pixels) != FRAME:
                    raise RuntimeError('Converter did not produce 5,120-byte image')
                outcome = client.ask(operation, pixels)
                sent += 1
                if operation == 'SAMPLE':
                    if outcome == 'COMPLETE':
                        print('  MOH enrolment: COMPLETE (RAM only)', flush=True)
                        complete = True
                        break
                    if outcome == 'RETRY QUALITY':
                        retries += 1
                        print('  MOH: image rejected, reposition finger', flush=True)
                    elif outcome.startswith('PROGRESS ') and outcome.endswith(' 12'):
                        print('  MOH: ' + outcome, flush=True)
                    else:
                        raise RuntimeError('Unexpected enrolment result: ' + outcome)
                else:
                    if outcome not in ('MATCH 1', 'MATCH 2', 'NO_MATCH',
                                       'AMBIGUOUS', 'RETRY QUALITY'):
                        raise RuntimeError('Unexpected match result: ' + outcome)
                    print('  MOH identification: ' + outcome + ' (experimental)', flush=True)
                    complete = True
                    break
                if first_only:
                    break
            elif kind == b'E':
                raise RuntimeError('Sensor helper: ' + payload.decode('utf-8', 'replace'))
            elif kind == b'D':
                break
        return complete, sent, retries
    finally:
        if proc.stdin and not proc.stdin.closed:
            try:
                proc.stdin.write(b'q')
                proc.stdin.flush()
            except (OSError, ValueError):
                pass
            proc.stdin.close()
        try:
            proc.wait(timeout=12)
        except subprocess.TimeoutExpired:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
        if proc.stdout:
            proc.stdout.close()


def prompt(msg: str):
    response = input(msg).strip().lower()
    if response in ('q', 'quit', 'exit', 'stop'):
        raise KeyboardInterrupt
    if response:
        raise ValueError('Only Enter starts a test; q cancels')


def live_main(moh_dir: Path, adapter: Path, python: Path) -> int:
    if os.geteuid() == 0:
        raise RuntimeError('Run as normal user, never as root')
    tools = moh_dir / 'tools'
    runner = tools / 'test_moh_isolated_live_identify.sh'
    helper_file = tools / 'auto_contact_capture.py'
    if any(p.is_symlink() or not p.is_file() for p in (runner, helper_file, adapter)):
        raise RuntimeError('Missing or symlinked trusted project component')
    if subprocess.run(['sudo', '-n', 'true'], stdout=subprocess.DEVNULL,
                      stderr=subprocess.DEVNULL, check=False).returncode != 0:
        raise RuntimeError('Run sudo -v first; the existing bounded USB helper needs it')
    # This imports exactly the tested image conversion function from the
    # feature branch, including the crucial polarity inversion.
    sys.path.insert(0, str(tools))
    from live_finger_identify import prepared_pixels

    client = AdapterClient([str(python), str(adapter), '--runner', str(runner)])
    helper = ['sudo', '-n', str(python), str(helper_file)]
    print('MOH IPC live experiment. Two different fingers, 12 usable scans each.')
    print('No persistent templates. No libfprint/fprintd/PAM changes.')
    print('Lift fully between scans; touch lightly without pressing power switch.')
    try:
        client.start()
        for slot in (1, 2):
            if client.ask(f'BEGIN {slot}') != 'BEGIN OK':
                raise RuntimeError('Failed to begin enrolment')
            total = 0
            done = False
            for batch in range(MAX_BATCHES):
                prompt(f'Finger {slot}: Enter starts bounded batch {batch+1}; q quits: ')
                done, count, rejected = capture_batch(client, 'SAMPLE', helper, prepared_pixels)
                total += count
                if done:
                    break
                if total >= MAX_FRAMES:
                    break
                print(f'  Batch ended: {count} impressions, {rejected} rejected.')
            if not done:
                raise RuntimeError(f'Finger {slot} enrolment did not complete within the safety budget')
        while True:
            prompt('Identify finger: Enter starts one fresh scan; q quits: ')
            done, count, _ = capture_batch(client, 'VERIFY', helper, prepared_pixels,
                                           first_only=True)
            if not done:
                print('No fresh impression captured')
    except (EOFError, KeyboardInterrupt):
        print('Session cancelled. Temporary MOH templates discarded.')
        return 0
    finally:
        client.close()


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--live', action='store_true', help='explicitly enable real sensor and sandboxed MOH')
    p.add_argument('--moh-dir', type=Path, default=Path.home()/'Projects/focaltech-5955-moh-test')
    args = p.parse_args()
    if not args.live:
        p.error('No default live operation. Pass --live explicitly to enable fingerprint capture')
    try:
        return live_main(args.moh_dir.resolve(), ROOT/'moh_adapter.py', Path(sys.executable))
    except (OSError, RuntimeError, ValueError) as exc:
        print('STOPPED: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
