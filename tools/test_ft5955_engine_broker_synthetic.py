#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Offline/non-root regression: system-fprintd relay -> Unix broker -> FAKE MOH.
No reader, no raw fingerprints, no Windows binaries, no system files/services.
Mock engine ONLY emits READY, RETRY QUALITY, BYE; never produces a MATCH.
"""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent
BROKER = HERE / "ft5955_engine_broker.py"
FRAME_SIZE = 5120

# Generated only in disposable mode-0700 /tmp directory. Not a credential.
MOCK_GATEWAY = r'''
import argparse
import sys
p = argparse.ArgumentParser()
p.add_argument("--moh-dir", required=True)
p.parse_args()
reader = sys.stdin.buffer
writer = sys.stdout.buffer
assert reader.readline() == b"MODE E\n"
writer.write(b"READY 1\n"); writer.flush()
assert reader.readline() == b"FRAME\n"
frame = reader.read(5120)
assert len(frame) == 5120
writer.write(b"RETRY QUALITY\n"); writer.flush()
assert reader.readline() == b"QUIT\n"
writer.write(b"BYE\n"); writer.flush()
'''


def main() -> int:
    if os.geteuid() == 0:
        print("STOP: synthetic broker test must NOT run as root/sudo.", file=sys.stderr)
        return 2
    if not BROKER.is_file():
        print("STOP: missing broker code.", file=sys.stderr)
        return 2
    with tempfile.TemporaryDirectory(prefix="ft5955-broker-test-") as dirname:
        root = Path(dirname)
        root.chmod(0o700)
        fake = root / "synthetic_gateway.py"
        fake.write_text(MOCK_GATEWAY, encoding="utf-8")
        fake.chmod(0o600)
        socket_path = root / "broker.sock"
        service = subprocess.Popen(
            [sys.executable, str(BROKER), "--serve", "--test-only",
             "--socket", str(socket_path), "--gateway", str(fake),
             "--moh-dir", str(root)],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE, text=True,
        )
        try:
            until = time.monotonic() + 6
            while not socket_path.exists():
                if service.poll() is not None or time.monotonic() >= until:
                    raise RuntimeError("Synthetic broker socket did not start")
                time.sleep(0.03)
            # Synthetic zeros only; do not use a genuine fingerprint image.
            scripted_input = b"MODE E\nFRAME\n" + bytes(FRAME_SIZE) + b"QUIT\n"
            client = subprocess.run(
                [sys.executable, str(BROKER), "--test-only",
                 "--socket", str(socket_path)],
                input=scripted_input, capture_output=True, timeout=20,
            )
            expected = b"READY 1\nRETRY QUALITY\nBYE\n"
            if client.returncode != 0 or client.stdout != expected:
                raise RuntimeError(
                    f"Relay protocol failed: code={client.returncode} "
                    f"out={client.stdout!r} stderr={client.stderr.decode(errors='replace')!r}"
                )
            service.wait(timeout=6)
            if service.returncode != 0:
                raise RuntimeError(f"Broker exit code {service.returncode}")
            print("PASS: root-free synthetic Unix broker / stdio relay flow")
            print("PASS: MODE E -> READY 1; 5120 synthetic bytes -> RETRY QUALITY; QUIT -> BYE")
            print("PASS: gateway runs in separate non-root process; temporary files removed")
            print("PASS: NO USB, enrolment, real biometric, MOH DLL, PAM or service changes")
            return 0
        finally:
            if service.poll() is None:
                service.terminate()
                try:
                    service.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    service.kill()
                    service.wait(timeout=3)
            if service.stderr is not None:
                service.stderr.close()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print("FAIL: broker synthetic check: " + str(exc), file=sys.stderr)
        sys.exit(1)
