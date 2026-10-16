#!/usr/bin/env python3
"""FT5955 experimental MOH IPC contract — SYNTHETIC only.

Line-oriented bounded local protocol for an eventual libfprint-side controller.
This prototype never calls USB, loads a vendor DLL or handles biometric bytes.
Messages (ASCII, one per line):
 HELLO -> READY 1
 BEGIN -> BEGIN OK
 SAMPLE ACCEPT -> PROGRESS <count> 12 | COMPLETE
 SAMPLE REJECT -> RETRY QUALITY
 VERIFY MATCH|NO_MATCH|REJECT -> MATCH|NO_MATCH|RETRY QUALITY
 CANCEL -> CANCELLED
 QUIT -> BYE

The mock MATCH action is deliberately synthetic and MUST NOT be used for authentication.
"""
import argparse
import subprocess
import sys
from dataclasses import dataclass

MAX_LINE = 128
STAGES = 12


@dataclass
class MockEngine:
    stage: int = 0
    active: bool = False
    enrolled: bool = False

    def handle(self, command: str) -> str:
        if command == 'HELLO':
            return 'READY 1'
        if command == 'BEGIN':
            self.stage = 0
            self.active = True
            self.enrolled = False
            return 'BEGIN OK'
        if command == 'SAMPLE REJECT' and self.active:
            return 'RETRY QUALITY'
        if command == 'SAMPLE ACCEPT' and self.active:
            self.stage += 1
            if self.stage == STAGES:
                self.active = False
                self.enrolled = True
                return 'COMPLETE'
            return f'PROGRESS {self.stage} {STAGES}'
        if command.startswith('VERIFY ') and self.enrolled:
            action = command.removeprefix('VERIFY ')
            return {'MATCH': 'MATCH', 'NO_MATCH': 'NO_MATCH',
                    'REJECT': 'RETRY QUALITY'}.get(action, 'ERROR BAD_COMMAND')
        if command == 'CANCEL':
            self.stage = 0
            self.active = False
            self.enrolled = False
            return 'CANCELLED'
        if command == 'QUIT':
            return 'BYE'
        return 'ERROR BAD_STATE'


def serve() -> int:
    engine = MockEngine()
    for raw in sys.stdin.buffer:
        if len(raw) > MAX_LINE or not raw.endswith(b'\n'):
            print('ERROR PROTOCOL', flush=True)
            return 2
        try:
            message = raw[:-1].decode('ascii')
        except UnicodeDecodeError:
            print('ERROR PROTOCOL', flush=True)
            return 2
        response = engine.handle(message)
        print(response, flush=True)
        if message == 'QUIT':
            return 0
    return 0


def smoke() -> int:
    command = [sys.executable, __file__, '--serve']
    with subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, text=True, bufsize=1) as proc:
        def request(message: str, expected: str) -> None:
            assert proc.stdin is not None and proc.stdout is not None
            proc.stdin.write(message + '\n')
            proc.stdin.flush()
            actual = proc.stdout.readline().strip()
            if actual != expected:
                raise AssertionError(f'{message}: expected {expected!r}, got {actual!r}')
            print(f'{message:18s} -> {actual}')
        try:
            request('HELLO', 'READY 1')
            request('BEGIN', 'BEGIN OK')
            request('SAMPLE REJECT', 'RETRY QUALITY')
            for n in range(1, STAGES):
                request('SAMPLE ACCEPT', f'PROGRESS {n} {STAGES}')
            request('SAMPLE ACCEPT', 'COMPLETE')
            request('VERIFY MATCH', 'MATCH')
            request('VERIFY NO_MATCH', 'NO_MATCH')
            request('VERIFY REJECT', 'RETRY QUALITY')
            request('CANCEL', 'CANCELLED')
            request('VERIFY MATCH', 'ERROR BAD_STATE')
            request('BEGIN', 'BEGIN OK')
            request('SAMPLE ACCEPT', 'PROGRESS 1 12')
            request('CANCEL', 'CANCELLED')
            request('QUIT', 'BYE')
            proc.stdin.close()
            exit_code = proc.wait(timeout=3)
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait(timeout=3)
        if exit_code != 0:
            raise AssertionError('mock engine exited unsuccessfully')
    print('PASS: 12-stage IPC mock, rejection, verification, cancellation and shutdown')
    return 0


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument('--serve', action='store_true')
    group.add_argument('--smoke-test', action='store_true')
    args = ap.parse_args()
    sys.exit(serve() if args.serve else smoke())
