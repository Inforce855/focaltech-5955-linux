#!/usr/bin/env python3
"""Measure *real* FocalTech 2808:5955 images with libfprint's own NBIS.

One finger press is enough for multiple tests; only numeric results are shown.
No fingerprints, templates, raw files, image previews or coordinates are saved.
Runs as the desktop user; only the existing bounded USB helper runs with sudo.
Alternatively --raw accepts ONE previously captured LOCAL private raw sample.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys

import numpy as np

from live_libfprint_bridge import (
    ROOT, HELPER, NATIVE_CLI, RAW_BYTES, WIDTH, HEIGHT,
    enlarge, normalize, read_record, stop_helper,
)

PROBE = ROOT / "native/build/ft5955_nbis_probe"
SCALES = (1, 2, 3, 4, 10)


def one_live_capture() -> bytes:
    command = ["sudo", "-n", sys.executable, str(HELPER)]
    proc = subprocess.Popen(
        command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, cwd=ROOT,
    )
    try:
        print("Lift your finger completely; then make ONE fresh touch.", flush=True)
        while True:
            record = read_record(proc.stdout)
            if record is None:
                detail = proc.stderr.read(300).decode("utf-8", "replace").strip()
                raise RuntimeError("USB helper stopped before capture: " + detail)
            kind, data = record
            if kind == b"S":
                print("Sensor: " + data.decode("utf-8", "replace"), flush=True)
            elif kind == b"F":
                if len(data) != RAW_BYTES:
                    raise RuntimeError("Invalid real sensor frame length")
                return data
            elif kind == b"E":
                raise RuntimeError("USB helper: " + data.decode("utf-8", "replace"))
            elif kind == b"D":
                raise RuntimeError("USB helper ended without an image: " + data.decode("utf-8", "replace"))
    finally:
        stop_helper(proc)


def describe(pixels: bytes) -> str:
    matrix = np.frombuffer(pixels, dtype=np.uint8).reshape(HEIGHT, WIDTH).astype(np.float32)
    std = float(matrix.std())
    x_delta = float(np.abs(np.diff(matrix, axis=1)).mean())
    y_delta = float(np.abs(np.diff(matrix, axis=0)).mean())
    black = float(np.count_nonzero(matrix == 0) / matrix.size * 100)
    white = float(np.count_nonzero(matrix == 255) / matrix.size * 100)
    return f"mean={matrix.mean():.1f} std={std:.1f} edgeX={x_delta:.1f} edgeY={y_delta:.1f} black={black:.1f}% white={white:.1f}%"


def probe_minutiae(image: bytes, width: int, height: int) -> int:
    result = subprocess.run(
        [str(PROBE), str(width), str(height)], input=image,
        capture_output=True, timeout=30, check=False,
    )
    stdout = result.stdout.decode("ascii", "replace").strip()
    if result.returncode or not stdout.startswith("MINUTIAE "):
        raise RuntimeError(
            "NBIS diagnostic failed: " + result.stderr.decode("utf-8", "replace")[:300]
            + ("; stdout=" + stdout[:100] if stdout else "")
        )
    return int(stdout.split()[1])


def diagnose(raw: bytes, scales: tuple[int, ...] = SCALES) -> list[tuple[str, int, str, int]]:
    outputs: list[tuple[str, int, str, int]] = []
    for method in ("contrast", "native-v3"):
        pixels = normalize(raw, method)
        print(f"{method:>10} raw 64x80 stats: {describe(pixels)}", flush=True)
        for scale in scales:
            enlarged = enlarge(pixels, scale, "linear")
            for polarity in ("normal", "inverted"):
                tested = enlarged if polarity == "normal" else enlarged.translate(INVERT_TABLE)
                try:
                    count = probe_minutiae(tested, WIDTH * scale, HEIGHT * scale)
                except (RuntimeError, subprocess.TimeoutExpired) as exc:
                    # Continue the rest of the real-image tests when one size
                    # isn't acceptable to NBIS. Never print pixel content.
                    count = -1
                    print(f"  {method:>9} {scale:>2}x {polarity:<8} : NBIS error: {exc}", flush=True)
                else:
                    print(f"  {method:>9} {scale:>2}x {polarity:<8} : {count:>3} minutiae", flush=True)
                outputs.append((method, scale, polarity, count))
    return outputs


INVERT_TABLE = bytes.maketrans(bytes(range(256)), bytes(reversed(range(256))))


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--live", action="store_true", help="One real fresh sensor press, no file created")
    group.add_argument("--raw", type=Path, help="One EXISTING LOCAL private 10240-byte raw file")
    args = p.parse_args()
    if not PROBE.is_file():
        p.error("Build NBIS probe first with bash tools/build_nbis_diagnostic.sh")
    if not NATIVE_CLI.is_file():
        p.error("Build native normalizer first: make -C native build/ft5955_normalize_cli")
    try:
        if args.live:
            if os.geteuid() == 0:
                p.error("Run as normal user, not root")
            raw = one_live_capture()
            print("Real sensor capture received IN MEMORY. No biometric file saved.", flush=True)
        else:
            raw = args.raw.read_bytes()
            if len(raw) != RAW_BYTES:
                raise ValueError("Raw file must be exactly 10240 bytes")
            print("Existing private real fingerprint read locally. No new file saved.", flush=True)
        results = diagnose(raw)
        positives = [r for r in results if r[3] > 0]
        print("\nRESULT:")
        if not positives:
            errors = sum(1 for r in results if r[3] < 0)
            print(f"No minutiae in the tested variants ({errors} NBIS errors). Inspect sensor calibration/row reconstruction next.")
        else:
            print(f"Detected minutiae in {len(positives)}/{len(results)} variants. These are FEATURE COUNTS, not proof of matching.")
            best = sorted(positives, key=lambda row: -row[3])[:5]
            for method, scale, polarity, count in best:
                print(f"  {method} / {scale}x / {polarity}: {count} minutiae")
        return 0
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired, EOFError) as exc:
        print(f"Diagnostic stopped: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
