#!/usr/bin/env python3
"""Real private FocalTech 2808:5955 capture evaluation, OFFLINE ONLY.

Runs our compiled native FT9362-inspired v3 normalizer on four existing
A1/A2/B1/B2 .raw captures, creates local/private 2x2 comparison images, and
prints genuine-versus-impostor exploratory correlations for both layouts.

This is NOT a fingerprint matcher, enrollment or authentication procedure.
No USB I/O, network, proprietary libraries or new biometric captures.
Images remain only in the gitignored local-data/native-real-test/ directory.
Share the terminal's aggregate scores, NEVER the generated fingerprint images.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import stat
import subprocess
import sys

from fingerprint_compare import compare, preprocess_samples, recent_four
from raw_decode_preview import private_directory
from raw_to_png import RAW_BYTES, greyscale_png, save_private, upscale_nn

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CAPTURES = ROOT / "local-data"
OUTPUT_DIRECTORY = DEFAULT_CAPTURES / "native-real-test"
EXECUTABLE = ROOT / "native/build/ft5955_normalize_cli"
LABELS = ("A1", "A2", "B1", "B2")
PAIRS = (
    ("A1 vs A2 (same A)", 0, 1),
    ("B1 vs B2 (same B)", 2, 3),
    ("A1 vs B1 (different)", 0, 2),
    ("A1 vs B2 (different)", 0, 3),
    ("A2 vs B1 (different)", 1, 2),
    ("A2 vs B2 (different)", 1, 3),
)
LAYOUTS = {"64x80": (64, 80), "80x64": (80, 64)}


def read_private_capture(path: Path) -> bytes:
    if path.is_symlink():
        raise ValueError("Refusing symlinked biometric input")
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_size != RAW_BYTES:
        raise ValueError(
            f"{path.name}: expected regular {RAW_BYTES}-byte private capture"
        )
    return path.read_bytes()


def convert_using_native(raw: bytes, executable: Path = EXECUTABLE) -> bytes:
    """Feed bytes to OUR local native code via stdin; do not save or upload raw."""
    if len(raw) != RAW_BYTES:
        raise ValueError("Expected exactly 10240 little-endian capture bytes")
    if executable.is_symlink() or not executable.is_file():
        raise ValueError(
            "Native converter is missing; build it with: "
            "make -C native build/ft5955_normalize_cli"
        )
    try:
        result = subprocess.run(
            [str(executable)], input=raw, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, check=False, timeout=15
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("Offline native converter timed out") from exc
    if result.returncode != 0:
        message = result.stderr.decode("utf-8", errors="replace").strip()
        raise ValueError(
            f"Native converter rejected capture ({result.returncode}): "
            f"{message[:250]}"
        )
    if len(result.stdout) != 5120:
        raise ValueError("Native converter returned an unexpected image length")
    return result.stdout


def contact_sheet(images: list[bytes], width: int, height: int, zoom: int) -> bytes:
    """Top row A1,A2; bottom row B1,B2; nearest-neighbour zoom."""
    if len(images) != 4 or any(len(im) != width * height for im in images):
        raise ValueError("Expected exactly four 5120-byte image arrays")
    if not 1 <= zoom <= 12:
        raise ValueError("Preview zoom must be 1 through 12")
    up = [upscale_nn(im, width, height, zoom) for im in images]
    row_bytes = width * zoom
    full_height = height * zoom
    combined = bytearray()
    for i, j in ((0, 1), (2, 3)):
        for row in range(full_height):
            start = row * row_bytes
            combined.extend(up[i][start:start + row_bytes])
            combined.extend(up[j][start:start + row_bytes])
    return greyscale_png(bytes(combined), 2 * row_bytes, 2 * full_height)


def analyse_layout(images: list[bytes], width: int, height: int) -> list[float]:
    """Display genuine/impostor correlations, NOT security match decisions."""
    processed = [
        preprocess_samples(tuple(image), width=width, height=height)
        for image in images
    ]
    values = []
    for label, left, right in PAIRS:
        score = compare(processed[left], processed[right], max_shift=6)
        values.append(score.correlation)
        print(
            f"  {label:<25} correlation={score.correlation:+.3f} "
            f"shift=({score.dx:+d},{score.dy:+d}) overlap={score.count}"
        )
    strongest_different = max(values[2:])
    print(f"  Strongest different-finger control: {strongest_different:+.3f}")
    print(f"  Same-finger A margin: {values[0] - strongest_different:+.3f}")
    print(f"  Same-finger B margin: {values[1] - strongest_different:+.3f}")
    print("  These margins are exploratory only; NOT identity verification.")
    return values


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "files", nargs="*", type=Path, metavar="RAW",
        help="four existing private files in A1 A2 B1 B2 order; "
             "default is latest labelled four in local-data"
    )
    parser.add_argument("--zoom", type=int, default=8)
    parser.add_argument(
        "--no-previews", action="store_true",
        help="print comparisons without creating private image files"
    )
    args = parser.parse_args()
    if len(args.files) not in (0, 4):
        parser.error("Supply exactly four RAW paths, or no paths for latest four")
    if not 1 <= args.zoom <= 12:
        parser.error("--zoom must be between 1 and 12")

    try:
        files = args.files if args.files else recent_four(DEFAULT_CAPTURES)
        raw = [read_private_capture(p) for p in files]
        images = [convert_using_native(data) for data in raw]
        print("FocalTech 2808:5955 — REAL-CAPTURE OFFLINE IMAGE EVALUATION")
        print("Native v3 algorithm; existing private scans; no sensor access.")
        print("Input: little-endian signed 16-bit; 5120 samples each.")
        for label, path in zip(LABELS, files):
            print(f"  {label}: {path.name}")
        if not args.no_previews:
            dest_dir = private_directory(OUTPUT_DIRECTORY)
        for layout, (width, height) in LAYOUTS.items():
            print(f"\nLayout {layout} — 2x2 A1 A2 / B1 B2:")
            if not args.no_previews:
                # The last A1 capture name makes the preview distinct for
                # independently recorded sessions. Never overwrite silently.
                filename = f"{files[0].stem}-v3-{layout}-contact.png"
                output = dest_dir / filename
                try:
                    save_private(
                        output, contact_sheet(images, width, height, args.zoom)
                    )
                    print(f"  Private preview saved: {output}")
                except FileExistsError:
                    print(f"  Private preview already exists (not overwritten): {output}")
            try:
                analyse_layout(images, width, height)
            except ValueError as exc:
                print(f"  Correlation unavailable: {exc}")
                print("  Inspect the local preview for excessive sensor artefacts.")
        print("\nPreview layout: A1 top-left, A2 top-right; "
              "B1 bottom-left, B2 bottom-right.")
        print("Images are personal biometric data: keep them private. "
              "Share ONLY the printed numerical scores.")
        print("No verification threshold, enrollment or fprintd/PAM changes.")
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"Offline real-capture test failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
