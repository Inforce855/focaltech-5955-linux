#!/usr/bin/env python3
"""Experimental, PRIVATE FocalTech 5955 little-endian grayscale previews.

USB is never accessed. Real fingerprint files are read locally and never
uploaded, logged as pixels or used for authentication. Creates local PNGs
to compare a conservative signed-value display against a tentative
row-offset correction. Neither rendering is a verified Windows algorithm.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import stat
from statistics import median
import sys

from raw_to_png import (
    RAW_BYTES, decode_samples, greyscale_png, save_private, upscale_nn,
)

SAMPLE_COUNT = 5120
ALLOWED_LAYOUTS = {"80x64": (80, 64), "64x80": (64, 80)}


def signed_clamp(samples: tuple[int, ...]) -> list[int]:
    """Windows-like *first step*: negative signed-16-bit words -> zero."""
    if len(samples) != SAMPLE_COUNT:
        raise ValueError(f"Expected {SAMPLE_COUNT} unsigned 16-bit samples")
    return [word if word < 0x8000 else 0 for word in samples]


def remove_row_offsets(values: list[int], width: int, height: int) -> list[int]:
    """TENTATIVE diagnostic: median-normalise each populated sensor row.

    Preserve true zero/background values. This is NOT a reconstruction of
    the proprietary correction routine, and can remove real ridge structure.
    """
    if len(values) != width * height:
        raise ValueError("Wrong pixel count for this layout")
    foreground = [v for v in values if v > 0]
    if len(foreground) < width * 4:
        return list(values)
    target = median(foreground)
    result = list(values)
    for y in range(height):
        first = y * width
        row = values[first:first + width]
        active = [v for v in row if v > 0]
        if len(active) < max(8, width // 4):
            continue
        difference = median(active) - target
        for x, value in enumerate(row):
            if value > 0:
                result[first + x] = max(1, min(32767, round(value - difference)))
    return result


def stretch_foreground(values: list[int]) -> bytes:
    """Display-only percentile stretch; do not manufacture negative pixels."""
    if len(values) != SAMPLE_COUNT:
        raise ValueError("Wrong sample count")
    nonzero = sorted(x for x in values if x > 0)
    if not nonzero:
        return bytes(SAMPLE_COUNT)
    low = nonzero[int((len(nonzero) - 1) * .01)]
    high = nonzero[int((len(nonzero) - 1) * .99)]
    if high <= low:
        high = low + 1
    return bytes(
        0 if v == 0 else max(1, min(255, round((v - low) * 254 / (high - low)) + 1))
        for v in values
    )


def preview_png(values: list[int], width: int, height: int, zoom: int) -> bytes:
    if not 1 <= zoom <= 16:
        raise ValueError("Zoom must be 1..16")
    pixels = stretch_foreground(values)
    enlarged = upscale_nn(pixels, width, height, zoom)
    return greyscale_png(enlarged, width * zoom, height * zoom)


def private_directory(path: Path) -> Path:
    if path.is_symlink():
        raise OSError("Output directory must not be a symlink")
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    metadata = path.stat()
    if not stat.S_ISDIR(metadata.st_mode) or metadata.st_mode & 0o077:
        raise OSError("Output directory must have private (0700) permissions")
    if metadata.st_uid != os.getuid():
        raise OSError("Output directory must be owned by the current user")
    return path


def read_capture(path: Path) -> bytes:
    if path.is_symlink():
        raise ValueError("Refusing a symlinked fingerprint capture")
    metadata = path.stat()
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_size != RAW_BYTES:
        raise ValueError(f"Expected a regular {RAW_BYTES}-byte .raw input")
    return path.read_bytes()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="one private 10240-byte .raw capture")
    parser.add_argument("--layout", choices=("80x64", "64x80", "both"), default="both")
    parser.add_argument("--output-dir", type=Path, default=Path("local-data"))
    parser.add_argument("--zoom", type=int, default=8)
    args = parser.parse_args()
    if not 1 <= args.zoom <= 16:
        parser.error("--zoom must be 1..16")
    try:
        raw = read_capture(args.input)
        samples = signed_clamp(decode_samples(raw, "little"))
        negative = sum(1 for x in decode_samples(raw, "little") if x >= 0x8000)
        print("FocalTech 2808:5955 — private image decoding experiment")
        print("LITTLE-endian signed samples; NO USB calls or network operations.")
        print(f"Negative signed samples clamped: {negative}/{SAMPLE_COUNT}.")
        print("The extra row correction is experimental, NOT a verified Windows copy.")
        output_dir = private_directory(args.output_dir)
        layouts = tuple(ALLOWED_LAYOUTS) if args.layout == "both" else (args.layout,)
        for layout in layouts:
            width, height = ALLOWED_LAYOUTS[layout]
            products = {
                "signed-clamped": samples,
                "row-normalised-EXPERIMENTAL": remove_row_offsets(samples, width, height),
            }
            for variant, values in products.items():
                name = f"{args.input.stem}-little-{layout}-{variant}-preview.png"
                dest = output_dir / name
                save_private(dest, preview_png(values, width, height, args.zoom))
                print(f"Private preview: {dest}  ({width * args.zoom} x {height * args.zoom})")
        print("These files remain private; do not commit or upload fingerprints.")
        return 0
    except (OSError, ValueError) as exc:
        print(f"Unable to generate private previews: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
