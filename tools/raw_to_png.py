#!/usr/bin/env python3
"""Convert a PRIVATE 80x64 raw, 16-bit FocalTech sample buffer to PNG.

Offline only; this tool does not access USB. Byte ordering and polarity are
hypotheses until validated against a real capture. No synthetic image output
is packaged with the project.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import struct
import zlib

WIDTH = 80
HEIGHT = 64
PIXELS = WIDTH * HEIGHT
RAW_BYTES = 2 * PIXELS
SIGNATURE = b"\x89PNG\r\n\x1a\n"


def png_chunk(name: bytes, data: bytes) -> bytes:
    return (struct.pack(">I", len(data)) + name + data
            + struct.pack(">I", zlib.crc32(name + data) & 0xffffffff))


def greyscale_png(values: bytes, width: int, height: int, *, bits: int = 8) -> bytes:
    if bits not in (8, 16):
        raise ValueError("Supported depths: 8, 16")
    row_bytes = width * (bits // 8)
    if len(values) != row_bytes * height:
        raise ValueError("Pixel data size doesn't match dimensions")
    scanlines = b"".join(
        b"\x00" + values[row * row_bytes:(row + 1) * row_bytes]
        for row in range(height)
    )
    ihdr = struct.pack(">IIBBBBB", width, height, bits, 0, 0, 0, 0)
    return (SIGNATURE + png_chunk(b"IHDR", ihdr)
            + png_chunk(b"IDAT", zlib.compress(scanlines, level=9))
            + png_chunk(b"IEND", b""))


def decode_samples(raw: bytes, byte_order: str) -> tuple[int, ...]:
    if len(raw) != RAW_BYTES:
        raise ValueError(f"Expected exactly {RAW_BYTES} raw bytes; got {len(raw)}")
    if byte_order not in ("big", "little"):
        raise ValueError("byte order must be 'big' or 'little'")
    return struct.unpack((">" if byte_order == "big" else "<") + f"{PIXELS}H", raw)


def to_8bit(values: tuple[int, ...]) -> bytes:
    """Robust contrast stretch for inspection, not verified sensor calibration."""
    ordered = sorted(values)
    low = ordered[int((len(ordered) - 1) * 0.01)]
    high = ordered[int((len(ordered) - 1) * 0.99)]
    if high <= low:
        low, high = ordered[0], ordered[-1]
    if high <= low:
        return bytes(PIXELS)
    return bytes(max(0, min(255, round((v - low) * 255 / (high - low)))) for v in values)


def upscale_nn(pixels: bytes, width: int, height: int, factor: int) -> bytes:
    if len(pixels) != width * height:
        raise ValueError("Invalid source pixels")
    if not 1 <= factor <= 16:
        raise ValueError("Zoom factor must be 1..16")
    return b"".join(
        b"".join(bytes((pix,)) * factor for pix in pixels[y * width:(y + 1) * width])
        * factor
        for y in range(height)
    )


def save_private(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as output:
        output.write(content)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Private 10240-byte raw capture; no USB access")
    parser.add_argument("--order", choices=("big", "little", "both"), default="both")
    parser.add_argument("--layout", choices=("80x64", "64x80"), default="80x64",
                        help="row-major pixel layout; 64x80 is experimental")
    parser.add_argument("--output-dir", type=Path, default=Path("local-data"))
    parser.add_argument("--zoom", type=int, default=8, help="Preview zoom (1..16, default 8)")
    args = parser.parse_args()
    if not 1 <= args.zoom <= 16:
        parser.error("--zoom must be between 1 and 16")
    try:
        raw = args.input.read_bytes()
        if len(raw) != RAW_BYTES:
            raise ValueError(f"Input must be {RAW_BYTES} bytes, got {len(raw)}")
        width, height = map(int, args.layout.split("x"))
        for order in (("big", "little") if args.order == "both" else (args.order,)):
            samples = decode_samples(raw, order)
            enhanced = to_8bit(samples)
            raw16 = b"".join(n.to_bytes(2, "big") for n in samples)
            prefix = f"{args.input.stem}-{order}"
            if args.layout != "80x64":
                prefix += f"-{args.layout}"
            products = {
                f"{prefix}-original16.png": greyscale_png(raw16, width, height, bits=16),
                f"{prefix}-contrast.png": greyscale_png(enhanced, width, height),
                f"{prefix}-preview.png": greyscale_png(
                    upscale_nn(enhanced, width, height, args.zoom),
                    width * args.zoom, height * args.zoom,
                ),
            }
            for name, data in products.items():
                dest = args.output_dir / name
                save_private(dest, data)
                print(f"Saved (private): {dest} ({len(data)} bytes)")
            print(f"{order}: sample range {min(samples)} to {max(samples)}; "
                  f"{len(set(samples))} distinct values")
    except (OSError, ValueError) as exc:
        parser.exit(1, f"Error: {exc}\n")
    print("Byte order, polarity and 80x64 versus 64x80 layout remain experimental.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
