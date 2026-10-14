#!/usr/bin/env python3
"""EXPERIMENTAL, memory-only FocalTech 5955 two-finger identification test.

Enroll 'Finger 1' and 'Finger 2' by lifting and pressing repeatedly; then
make new touches to see which enrolled template the vendor matcher reports.
No fingerprint images, BIRs, templates or labels are saved, uploaded, printed
or exposed outside the isolated matching process. All disappear on exit.
No libfprint, fprintd, KDE, PAM, or real biometric database changes.

Run as a regular user with explicit --send after 'sudo -v'. Requires the
matching privately held Windows driver archive. USB I/O is performed only
by the existing 8-touch/240-poll bounded helper, not by the sandboxed DLL.
"""
from __future__ import annotations

import argparse
from collections import deque
import os
from pathlib import Path
import subprocess
import sys
import threading

from live_contact_viewer import read_record
from raw_to_png import decode_samples, to_8bit

HERE = Path(__file__).resolve().parent
ENGINE_SCRIPT = HERE / "test_moh_isolated_live_identify.sh"
USB_HELPER = HERE / "auto_contact_capture.py"


class Cancelled(Exception):
    """Operator cancelled a test without changing system authentication."""


def prepared_pixels(raw: bytes) -> bytes:
    """64x80, little-endian percentile-contrast, then Windows-like inversion."""
    pixels = to_8bit(decode_samples(raw, "little"))
    if len(pixels) != 5120:
        raise ValueError("Unexpected sensor frame dimensions")
    return bytes(255 - v for v in pixels)


def interpret_response(line: str) -> str:
    """Interpret only the deliberately minimal engine protocol."""
    if line == "IDENTIFY 1":
        return "Finger 1 — MATCH"
    if line == "IDENTIFY 2":
        return "Finger 2 — MATCH"
    if line == "IDENTIFY NONE":
        return "No match to either enrolled finger (experimental result)"
    if line == "IDENTIFY AMBIGUOUS":
        return "AMBIGUOUS — both fingers matched; do not identify this capture"
    if line == "IDENTIFY REJECTED":
        return "Scan rejected; lift, reposition and try again"
    raise ValueError("Unexpected identification response: " + line)


class IsolatedEngine:
    def __init__(self, archive: Path):
        self.archive = archive
        self.proc: subprocess.Popen | None = None
        self.stderr_lines: deque[str] = deque(maxlen=12)

    def _drain_stderr(self) -> None:
        proc = self.proc
        if proc is None or proc.stderr is None:
            return
        for raw in iter(proc.stderr.readline, b""):
            line = raw.decode("utf-8", "replace").strip()
            # Logs may contain diagnostic pointers/values. Keep them local,
            # never copy them to an external service or saved logfile.
            if line:
                self.stderr_lines.append(line[:240])

    def start(self) -> None:
        self.proc = subprocess.Popen(
            ["bash", str(ENGINE_SCRIPT), str(self.archive)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=HERE.parent,
            bufsize=0,
        )
        threading.Thread(target=self._drain_stderr, daemon=True).start()
        for _ in range(24):
            line = self._next_line()
            if line == "READY":
                return
            if line.startswith("ERROR "):
                raise RuntimeError("Engine initialisation failed: " + line)
        raise RuntimeError("Isolated engine did not report READY")

    def _next_line(self) -> str:
        if self.proc is None or self.proc.stdout is None:
            raise RuntimeError("Engine not running")
        raw = self.proc.stdout.readline()
        if not raw:
            details = " | ".join(list(self.stderr_lines)[-3:])
            raise RuntimeError("Engine exited early" + (": " + details if details else ""))
        return raw.decode("utf-8", "replace").strip()

    def frame(self, operation: bytes, pixels: bytes) -> str:
        if operation not in (b"1", b"2", b"V") or len(pixels) != 5120:
            raise ValueError("Invalid bounded engine frame")
        if self.proc is None or self.proc.stdin is None:
            raise RuntimeError("Engine not running")
        if self.proc.poll() is not None:
            raise RuntimeError("Engine ended before this capture")
        self.proc.stdin.write(operation + pixels)
        self.proc.stdin.flush()
        for _ in range(4):
            line = self._next_line()
            if line.startswith(("ENROL ", "IDENTIFY ", "ERROR ")):
                if line.startswith("ERROR "):
                    raise RuntimeError("Engine rejected operation: " + line)
                return line
        raise RuntimeError("Unexpected engine response")

    def close(self) -> None:
        proc = self.proc
        if proc is None:
            return
        if proc.poll() is None and proc.stdin:
            try:
                proc.stdin.write(b"Q")
                proc.stdin.flush()
            except (BrokenPipeError, OSError):
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
        self.proc = None


def prompt(message: str) -> None:
    try:
        answer = input(message).strip().lower()
    except (EOFError, KeyboardInterrupt):
        raise Cancelled() from None
    if answer in ("q", "quit", "exit", "stop"):
        raise Cancelled()


def touch_batch(engine: IsolatedEngine, operation: bytes,
                *, first_only: bool = False) -> tuple[bool, int]:
    """Use exactly one bounded USB-helper session. Return (complete, frames)."""
    proc = subprocess.Popen(
        ["sudo", "-n", sys.executable, str(USB_HELPER)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        cwd=HERE.parent,
        bufsize=0,
    )
    captured = 0
    done = False
    try:
        assert proc.stdout is not None
        while True:
            item = read_record(proc.stdout)
            if item is None:
                break
            kind, data = item
            if kind == b"S":
                msg = data.decode("utf-8", "replace")
                if "Finger off" in msg or "Lift" in msg:
                    print("  " + msg, flush=True)
            elif kind == b"F":
                captured += 1
                pixels = prepared_pixels(data)
                response = engine.frame(operation, pixels)
                if operation == b"V":
                    print("  " + interpret_response(response), flush=True)
                    done = True
                    break
                parts = response.split()
                if len(parts) != 3 or parts[:2] != ["ENROL", operation.decode("ascii")]:
                    raise RuntimeError("Unexpected enrolment response: " + response)
                outcome = parts[2]
                if outcome == "ADDED":
                    print("  Impression accepted — more required", flush=True)
                elif outcome == "REJECTED":
                    print("  Impression rejected — reposition finger", flush=True)
                elif outcome == "COMPLETE":
                    print("  12-impression enrolment committed in sandbox memory", flush=True)
                    done = True
                    break
                else:
                    raise RuntimeError("Unknown engine enrolment result")
                if first_only:
                    break
            elif kind == b"E":
                raise RuntimeError("USB capture failed: " + data.decode("utf-8", "replace"))
            elif kind == b"D":
                break
        return done, captured
    finally:
        if proc.stdin and not proc.stdin.closed:
            try:
                proc.stdin.write(b"q")
                proc.stdin.flush()
            except (BrokenPipeError, OSError):
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
        if proc.stdout and not proc.stdout.closed:
            proc.stdout.close()


def run_session(engine: IsolatedEngine) -> None:
    print("\nLive experimental identification — no template files or Linux login changes")
    print("The first two fingers MUST be different. Give each finger fresh touches.")
    print("Keep your finger lifted for at least half a second between captures.")
    print("Enter starts each bounded batch; type q then Enter to quit at any prompt.")

    for slot in (b"1", b"2"):
        name = slot.decode("ascii")
        print(f"\nENROL FINGER {name}: 12 accepted impressions required.")
        for batch in range(1, 14):
            prompt(f"Finger {name}: press Enter to begin capture batch {batch} (q quits): ")
            complete, count = touch_batch(engine, slot)
            if complete:
                break
            print(f"  Batch finished ({count} touches). Additional impressions needed.")
        else:
            raise RuntimeError(f"Finger {name} failed to complete within the bounded session limit")
        print(f"Finger {name} enrolled TEMPORARILY. Do not switch labels during its enrolment.")

    print("\nBoth temporary templates are ready. Now test ANY finger, one fresh touch at a time.")
    while True:
        prompt("\nLift finger fully. Press Enter to identify next touch (q quits): ")
        complete, count = touch_batch(engine, b"V", first_only=True)
        if not count:
            print("  No fresh touch captured within this bounded session.")
        elif not complete:
            print("  No identification result returned.")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive", type=Path, required=True)
    p.add_argument("--send", action="store_true",
                   help="Explicitly authorise bounded real USB sensor interaction")
    args = p.parse_args()
    if not args.send:
        p.error("Use --send for live captures; this is not an offline replay")
    if os.geteuid() == 0:
        p.error("Run as a regular desktop user; use sudo -v separately")
    if not args.archive.is_file():
        p.error("FocalTech matching driver archive not found")
    if subprocess.run(["sudo", "-n", "true"], check=False,
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode != 0:
        p.error("USB helper needs cached sudo credentials: run sudo -v first")
    engine = IsolatedEngine(args.archive.resolve())
    try:
        print("Preparing isolated, temporary two-finger matcher...")
        engine.start()
        run_session(engine)
    except Cancelled:
        print("\nStopped by operator. Both templates will be discarded.")
    except (OSError, ValueError, RuntimeError) as exc:
        print("TEST STOPPED: " + str(exc), file=sys.stderr)
        return 1
    finally:
        engine.close()
    print("Session ended. No fingerprints or templates saved.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
