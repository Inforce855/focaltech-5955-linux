#!/usr/bin/env python3
"""v0.9.4 diagnostic IPC proxy: inject exactly one verify RETRY QUALITY.

Runs ONLY as opt-in FT5955_ENGINE_GATEWAY during the verification quality test.
It does not load a DLL, access USB, persist templates, open sockets, or install
anything. The original audited gateway remains the child sandbox supervisor.
"""
from __future__ import annotations
import os
from pathlib import Path
import select
import signal
import subprocess
import sys
import time

FRAME = 5120
MAX_TEMPLATE = 1 << 20
MAX_LINE = 127
TIMEOUT = 120.0


def erase(buffer: bytearray) -> None:
    buffer[:] = b'\0' * len(buffer)


def line(stream, limit=MAX_LINE) -> bytes:
    value = stream.readline(limit + 1)
    if not value or len(value) > limit or not value.endswith(b'\n'):
        raise RuntimeError('Invalid/closed diagnostic command')
    if any((x < 32 and x != 10) or x > 126 for x in value):
        raise RuntimeError('Non-ASCII diagnostic command')
    return value


def child_exact(proc: subprocess.Popen, length: int) -> bytearray:
    result = bytearray()
    fd = proc.stdout.fileno()
    deadline = time.monotonic() + TIMEOUT
    try:
        while len(result) < length:
            remain = deadline - time.monotonic()
            if remain <= 0 or not select.select([fd], [], [], remain)[0]:
                raise RuntimeError('Original gateway timed out')
            chunk = os.read(fd, min(65536, length - len(result)))
            if not chunk:
                raise RuntimeError('Original gateway closed stdout')
            result.extend(chunk)
        return result
    except BaseException:
        erase(result)
        raise


def child_line(proc) -> bytes:
    result = bytearray()
    try:
        for _ in range(MAX_LINE):
            b = child_exact(proc, 1)
            if b == b'\n':
                return bytes(result) + b'\n'
            if b[0] < 32 or b[0] > 126:
                raise RuntimeError('Malformed original gateway reply')
            result.extend(b)
        raise RuntimeError('Oversized original gateway reply')
    finally:
        erase(result)


def parent_exact(size: int) -> bytearray:
    result = bytearray()
    try:
        while len(result) < size:
            data = sys.stdin.buffer.read(size - len(result))
            if not data:
                raise RuntimeError('Truncated parent IPC binary payload')
            result.extend(data)
        return result
    except BaseException:
        erase(result)
        raise


def send_to_child(proc, data: bytes | bytearray) -> None:
    proc.stdin.write(data)
    proc.stdin.flush()


def send_to_parent(data: bytes | bytearray) -> None:
    sys.stdout.buffer.write(data)
    sys.stdout.buffer.flush()


def shutdown(proc) -> None:
    if proc is None:
        return
    if proc.poll() is None:
        try:
            send_to_child(proc, b'QUIT\n')
        except (BrokenPipeError, OSError, ValueError):
            pass
    try:
        proc.wait(timeout=4)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            proc.wait()
    for stream in (proc.stdin, proc.stdout):
        if stream:
            stream.close()


def main() -> int:
    if os.geteuid() == 0 or os.environ.get('FT5955_QUALITY_PROBE_ENABLE') != '1':
        raise RuntimeError('Non-root opt-in diagnostic only')
    original = os.environ.get('FT5955_ORIGINAL_ENGINE_GATEWAY', '')
    if not original or not os.path.isabs(original):
        raise RuntimeError('Missing absolute FT5955_ORIGINAL_ENGINE_GATEWAY')
    target = Path(original).resolve(strict=True)
    if target == Path(__file__).resolve() or not target.is_file():
        raise RuntimeError('Invalid original engine gateway')
    if not target.name == 'engine_gateway.py':
        raise RuntimeError('Expected original engine_gateway.py')
    proc = None
    injected = False
    mode = None
    initialized = False
    try:
        proc = subprocess.Popen([sys.executable, str(target)], stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                bufsize=0, start_new_session=True)
        while True:
            command = line(sys.stdin.buffer)
            if command == b'QUIT\n':
                send_to_parent(b'BYE\n')
                break
            if not initialized and command == b'MODE E\n':
                # Enrolment is simply forwarded; no deliberate rejection.
                mode = 'E'
                send_to_child(proc, command)
            elif not initialized and command.startswith(b'MODE V '):
                fields = command.rstrip(b'\n').split()
                if len(fields) != 4 or not fields[2].isdigit() or not fields[3].isdigit():
                    raise RuntimeError('Invalid verification header')
                size, subfactor = int(fields[2]), int(fields[3])
                if not (1 <= size <= MAX_TEMPLATE and 0 <= subfactor <= 255):
                    raise RuntimeError('Invalid verification template bounds')
                blob = parent_exact(size)
                try:
                    send_to_child(proc, command)
                    send_to_child(proc, blob)
                finally:
                    erase(blob)
                mode = 'V'
            elif initialized and command == b'FRAME\n':
                frame = parent_exact(FRAME)
                try:
                    if mode == 'V' and not injected:
                        # Consume but DO NOT forward the first real captured frame.
                        # The actual matcher sees only the subsequent physical scan.
                        injected = True
                        send_to_parent(b'RETRY QUALITY\n')
                        continue
                    send_to_child(proc, command)
                    send_to_child(proc, frame)
                finally:
                    erase(frame)
                response = child_line(proc)
                if response not in (b'MATCH\n', b'NO_MATCH\n', b'RETRY QUALITY\n',
                                    b'COMPLETE\n') and not (
                                        mode == 'E' and response.startswith(b'PROGRESS ')):
                    raise RuntimeError('Unexpected original gateway response')
                send_to_parent(response)
                if response == b'COMPLETE\n':
                    header = child_line(proc)
                    bits = header.strip().split()
                    if len(bits) != 3 or bits[0] != b'TEMPLATE' or (
                        not bits[1].isdigit()) or (not bits[2].isdigit()):
                        raise RuntimeError('Bad original template header')
                    n, subfactor = int(bits[1]), int(bits[2])
                    if not (1 <= n <= MAX_TEMPLATE and 0 <= subfactor <= 255):
                        raise RuntimeError('Invalid original template bounds')
                    template = child_exact(proc, n)
                    try:
                        send_to_parent(header)
                        send_to_parent(template)
                    finally:
                        erase(template)
                continue
            else:
                raise RuntimeError('Unexpected parent IPC state')
            ready = child_line(proc)
            if ready != b'READY 1\n':
                raise RuntimeError('Original gateway not READY')
            send_to_parent(ready)
            initialized = True
        return 0
    finally:
        shutdown(proc)


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (RuntimeError, OSError, ValueError) as exc:
        print('FT5955 diagnostic proxy refused/failed: ' + type(exc).__name__,
              file=sys.stderr)
        raise SystemExit(3)
