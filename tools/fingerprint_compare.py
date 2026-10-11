#!/usr/bin/env python3
"""Offline experimental similarity comparison for three PRIVATE FT936x captures.

No USB access, no image output, no matching-template database and no changes
at all to authentication. Scores are exploratory image correlations, NOT a
biometric identity check. Samples must stay on the user's own computer.

Uses robust intensity scaling, a two-scale spatial filter and an exhaustive
small x/y translation search. Processing is intentionally stdlib-only.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import math
from pathlib import Path
import stat
import sys

from raw_to_png import WIDTH, HEIGHT, RAW_BYTES, decode_samples

PIXELS = WIDTH * HEIGHT


@dataclass(frozen=True)
class Processed:
    data: tuple[float, ...]
    detail_rms: float
    raw_range: int


@dataclass(frozen=True)
class Comparison:
    correlation: float
    dx: int
    dy: int
    count: int


def box_average(pixels: list[float], radius: int) -> list[float]:
    """Compute clipped-window box averages with a summed-area table."""
    stride = WIDTH + 1
    integral = [0.0] * ((HEIGHT + 1) * stride)
    for y in range(HEIGHT):
        row_sum = 0.0
        for x in range(WIDTH):
            row_sum += pixels[y * WIDTH + x]
            integral[(y + 1) * stride + x + 1] = (
                integral[y * stride + x + 1] + row_sum
            )
    out = []
    for y in range(HEIGHT):
        top, bottom = max(0, y - radius), min(HEIGHT, y + radius + 1)
        for x in range(WIDTH):
            left, right = max(0, x - radius), min(WIDTH, x + radius + 1)
            sum_pixels = (integral[bottom * stride + right]
                          - integral[top * stride + right]
                          - integral[bottom * stride + left]
                          + integral[top * stride + left])
            out.append(sum_pixels / ((bottom - top) * (right - left)))
    return out


def preprocess_samples(samples: tuple[int, ...]) -> Processed:
    """Band-pass normalise image detail without learning individual fingers."""
    if len(samples) != PIXELS:
        raise ValueError('Image must contain exactly 80 x 64 sensor samples')
    sorted_values = sorted(samples)
    low = sorted_values[int(0.01 * (PIXELS - 1))]
    high = sorted_values[int(0.99 * (PIXELS - 1))]
    if high - low < 16:
        raise ValueError('Insufficient raw image variation for a comparison')
    scale = 1.0 / (high - low)
    levels = [min(1.0, max(0.0, (v - low) * scale)) for v in samples]
    fine = box_average(levels, 1)
    background = box_average(levels, 5)
    detail = [x - y for x, y in zip(fine, background)]
    # Centre and normalise on the interior, avoiding variable edge borders.
    margin = 6
    interior = [detail[y * WIDTH + x]
                for y in range(margin, HEIGHT - margin)
                for x in range(margin, WIDTH - margin)]
    mean = sum(interior) / len(interior)
    rms = math.sqrt(sum((v - mean) ** 2 for v in interior) / len(interior))
    if rms < 0.003:
        raise ValueError('Very little spatial detail; a similarity score would be misleading')
    return Processed(tuple((d - mean) / rms for d in detail), rms, high - low)


def load_capture(path: Path, order: str) -> Processed:
    if path.is_symlink():
        raise ValueError(f'Refusing symlinked fingerprint file: {path.name}')
    meta = path.stat()
    if not stat.S_ISREG(meta.st_mode):
        raise ValueError(f'Not a regular file: {path.name}')
    if meta.st_size != RAW_BYTES:
        raise ValueError(f'Expected {RAW_BYTES} bytes in {path.name}; got {meta.st_size}')
    return preprocess_samples(decode_samples(path.read_bytes(), order))


def correlation_shift(a: tuple[float, ...], b: tuple[float, ...],
                      dx: int, dy: int, margin: int = 6) -> tuple[float, int]:
    """Pearson correlation on the shared area, shifted b relative to a."""
    min_x = max(margin, margin - dx)
    max_x = min(WIDTH - margin, WIDTH - margin - dx)
    min_y = max(margin, margin - dy)
    max_y = min(HEIGHT - margin, HEIGHT - margin - dy)
    n = (max_x - min_x) * (max_y - min_y)
    if n < 2000:
        return -1.0, n
    sa = sb = saa = sbb = sab = 0.0
    for y in range(min_y, max_y):
        a_base = y * WIDTH
        b_base = (y + dy) * WIDTH
        for x in range(min_x, max_x):
            va = a[a_base + x]
            vb = b[b_base + x + dx]
            sa += va
            sb += vb
            saa += va * va
            sbb += vb * vb
            sab += va * vb
    va = saa - sa * sa / n
    vb = sbb - sb * sb / n
    if va <= 1e-10 or vb <= 1e-10:
        return -1.0, n
    return max(-1.0, min(1.0, (sab - sa * sb / n) / math.sqrt(va * vb))), n


def compare(a: Processed, b: Processed, *, max_shift: int = 6) -> Comparison:
    if not 0 <= max_shift <= 8:
        raise ValueError('max_shift must be in 0..8 pixels')
    best = Comparison(-1.0, 0, 0, 0)
    for dy in range(-max_shift, max_shift + 1):
        for dx in range(-max_shift, max_shift + 1):
            score, n = correlation_shift(a.data, b.data, dx, dy)
            if score > best.correlation:
                best = Comparison(score, dx, dy, n)
    return best


def recent_three(folder: Path) -> list[Path]:
    if folder.is_symlink():
        raise ValueError('Refusing symlinked local-data directory')
    candidates = [p for p in folder.glob('fingerprint_*.raw')
                  if p.is_file() and not p.is_symlink()]
    if len(candidates) < 3:
        raise ValueError(f'Need three .raw fingerprint captures; found {len(candidates)} in {folder}')
    ordered = sorted(candidates, key=lambda p: (p.stat().st_mtime_ns, p.name))
    return ordered[-3:]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('files', metavar='RAW', nargs='*', type=Path,
                        help='three chronological 10240-byte raw captures: finger A, B, A')
    parser.add_argument('--latest-three', action='store_true',
                        help='use three most recently modified fingerprint_*.raw in local-data')
    parser.add_argument('--directory', type=Path, default=Path('local-data'),
                        help='capture directory used with --latest-three')
    parser.add_argument('--order', choices=('big', 'little'), default='big')
    parser.add_argument('--max-shift', type=int, choices=range(0, 9), default=6,
                        metavar='{0..8}', help='pixel translation window (default 6)')
    args = parser.parse_args()
    if args.latest_three and args.files:
        parser.error('Use either --latest-three or exactly three RAW filenames, not both')
    if not args.latest_three and len(args.files) != 3:
        parser.error('Provide three RAW filenames in A/B/A order, or --latest-three')
    try:
        files = recent_three(args.directory) if args.latest_three else args.files
        print('FocalTech 2808:5955 — OFFLINE image-similarity experiment')
        print('No USB access. No fingerprint output saved, uploaded or enrolled.')
        print(f'Decoding: {args.order}-endian; maximum translation: {args.max_shift} px')
        for label, filename in zip(('A1', 'B', 'A2'), files):
            print(f'  {label}: {filename.name}')
        samples = [load_capture(p, args.order) for p in files]
        for label, data in zip(('A1', 'B', 'A2'), samples):
            print(f'  {label} detail RMS: {data.detail_rms:.4f} (diagnostic only)')
        comparisons = [
            ('A1 vs A2 (same-finger hypothesis)', 0, 2),
            ('A1 vs B  (different-finger control)', 0, 1),
            ('A2 vs B  (different-finger control)', 2, 1),
        ]
        scores = []
        for label, i, j in comparisons:
            r = compare(samples[i], samples[j], max_shift=args.max_shift)
            print(f'  {label}: correlation {r.correlation:+.3f}, '
                  f'shift x={r.dx:+d} y={r.dy:+d} (overlap {r.count} px)')
            scores.append(r.correlation)
        separation = scores[0] - max(scores[1:])
        print(f'Same-finger correlation minus strongest control: {separation:+.3f}')
        if separation > 0:
            print('Observed ranking: same-finger pair is most similar.')
        else:
            print('Observed ranking: same-finger pair is NOT the most similar.')
        print('IMPORTANT: These are not verified identity matches, security thresholds,')
        print('or proof of liveness. Static sensor artefacts may bias correlations.')
        return 0
    except (OSError, ValueError) as exc:
        print(f'Unable to compare captures: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
