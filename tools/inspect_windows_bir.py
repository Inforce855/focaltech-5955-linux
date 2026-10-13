#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Inspect a private Windows WinBioCaptureSample BIR locally.

Default: read-only, structural metadata and aggregate statistics ONLY.
Opt-in --extract-candidate: create a private experimental 64x80 P5 PGM from
the vendor block's last 5120 bytes if the block is exactly 5136 bytes.
That layout is an unverified hypothesis, NOT an established FocalTech format.
No biometric bytes, pixels, fingerprint images or templates are printed.
Never upload the input BIR or generated PGM to a repository.
"""
from __future__ import annotations

import argparse
import math
import os
from pathlib import Path
import struct
import sys

W, H = 64, 80
PIXELS = W * H
VENDOR_PREFIX = 16
MAX_FILE = 8 * 1024 * 1024


def blocks_for_bir(data: bytes) -> dict[str, tuple[int, int]]:
    if not 32 <= len(data) <= MAX_FILE:
        raise ValueError("Unexpected file size; expected 32 bytes to 8 MiB")
    blocks: dict[str, tuple[int, int]] = {}
    nonempty = []
    for i, name in enumerate(("Header", "Standard", "Vendor", "Signature")):
        size, offset = struct.unpack_from("<II", data, i * 8)
        if size:
            if offset < 32 or offset + size > len(data):
                raise ValueError(f"{name} offset/size exceeds BIR boundaries")
            nonempty.append((offset, offset + size, name))
        elif offset:
            raise ValueError(f"{name} has zero size but nonzero offset")
        blocks[name] = (offset, size)
    for previous, current in zip(sorted(nonempty), sorted(nonempty)[1:]):
        if previous[1] > current[0]:
            raise ValueError(f"Overlapping blocks: {previous[2]} and {current[2]}")
    if blocks["Header"][1] < 48:
        raise ValueError("Invalid BIR header size; need at least 48 bytes")
    return blocks


def image_stats(pixels: bytes) -> str:
    n = len(pixels)
    mean = sum(pixels) / n
    variance = sum((value - mean) ** 2 for value in pixels) / n
    counts = [0] * 256
    for value in pixels:
        counts[value] += 1
    entropy = -sum((count / n) * math.log2(count / n) for count in counts if count)
    dx = sum(
        abs(pixels[y * W + x] - pixels[y * W + x + 1])
        for y in range(H) for x in range(W - 1)
    ) / (H * (W - 1))
    dy = sum(
        abs(pixels[y * W + x] - pixels[(y + 1) * W + x])
        for y in range(H - 1) for x in range(W)
    ) / ((H - 1) * W)
    return (f"Mean={mean:.1f}, SD={math.sqrt(variance):.1f}, "
            f"entropy={entropy:.2f} bits, adjacent differences "
            f"horizontal={dx:.1f} vertical={dy:.1f}")


def write_private_pgm(out: Path, pixels: bytes) -> None:
    if out.suffix.lower() != ".pgm":
        raise ValueError("Output filename must end in .pgm")
    if out.is_symlink():
        raise ValueError("Refusing to write through a symlink")
    out.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(out, flags, 0o600)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(f"P5\n{W} {H}\n255\n".encode("ascii"))
            stream.write(pixels)
    except BaseException:
        try:
            out.unlink()
        except OSError:
            pass
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bir", type=Path, help="Local private Windows .bir file")
    parser.add_argument("--extract-candidate", metavar="OUTPUT.pgm", type=Path,
                        help="Opt-in experimental 64x80 PGM (private file, never upload)")
    args = parser.parse_args()

    if not args.bir.is_file() or args.bir.is_symlink():
        parser.error("BIR must be a regular local file, not a symlink")
    if args.bir.stat().st_size > MAX_FILE:
        parser.error("BIR is too large")
    data = args.bir.read_bytes()
    try:
        blocks = blocks_for_bir(data)
    except ValueError as exc:
        parser.error(str(exc))

    print("Windows BIR structural inspection — no biometric data printed")
    print(f"File size: {len(data)} bytes")
    for name, (offset, size) in blocks.items():
        print(f"  {name:9s} offset={offset:6d} size={size:6d}")

    head_offset, _ = blocks["Header"]
    flags = data[head_offset + 4]
    print(f"BIR data flags: 0x{flags:02X} "
          f"(raw={bool(flags & 0x20)}, encrypted={bool(flags & 0x02)})")
    std_offset, std_size = blocks["Standard"]
    if std_size >= 40:
        std = data[std_offset:std_offset + std_size]
        format_id, version = struct.unpack_from("<II", std, 8)
        count, depth, compression = std[32], std[34], std[35]
        expected_ansi = (format_id == 0x46495200 and version == 0x30313000)
        print(f"Standard block: ANSI-381 header recognized={expected_ansi}; "
              f"records={count}; pixel_depth={depth}; compression={compression}")
        if std_size == 40:
            print("Standard block contains only a 40-byte header; "
                  "no image-record bytes follow it.")
    vendor_offset, vendor_size = blocks["Vendor"]
    if vendor_size != PIXELS + VENDOR_PREFIX:
        print(f"Candidate check: not applicable; vendor size {vendor_size} "
              f"does not equal {PIXELS}+{VENDOR_PREFIX}.")
        if args.extract_candidate:
            parser.error("Refusing extraction: unexpected vendor block size")
        return 0

    print("Candidate check: vendor block is 16 + 5120 bytes; "
          "possible 64x80 8-bit image (UNVERIFIED).")
    if flags & 0x02:
        print("Candidate inspection blocked: BIR declares encrypted data.")
        if args.extract_candidate:
            parser.error("Refusing extraction of encrypted biometric data")
        return 0
    pixels = data[vendor_offset + VENDOR_PREFIX:vendor_offset + vendor_size]
    print("Candidate aggregate statistics: " + image_stats(pixels))
    print("These statistics do not prove that the vendor bytes represent pixels.")
    if args.extract_candidate:
        try:
            write_private_pgm(args.extract_candidate, pixels)
        except (OSError, ValueError) as exc:
            parser.error(str(exc))
        print("Private experimental PGM written to " + str(args.extract_candidate))
        print("It is not validated as an image; view locally before using it "
              "in any engine tests. Do not put it in GitHub.")
    else:
        print("No fingerprint image saved. Use --extract-candidate to opt in.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
