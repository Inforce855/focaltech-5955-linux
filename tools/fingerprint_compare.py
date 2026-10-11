#!/usr/bin/env python3
"""Offline experimental similarity comparison for three or four PRIVATE FT936x captures.

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
    width: int = WIDTH
    height: int = HEIGHT


@dataclass(frozen=True)
class Comparison:
    correlation: float
    dx: int
    dy: int
    count: int


def box_average(pixels: list[float], radius: int, *, width: int = WIDTH,
                height: int = HEIGHT) -> list[float]:
    """Compute clipped-window box averages with a summed-area table."""
    stride = width + 1
    integral = [0.0] * ((height + 1) * stride)
    for y in range(height):
        row_sum = 0.0
        for x in range(width):
            row_sum += pixels[y * width + x]
            integral[(y + 1) * stride + x + 1] = (
                integral[y * stride + x + 1] + row_sum
            )
    out = []
    for y in range(height):
        top, bottom = max(0, y - radius), min(height, y + radius + 1)
        for x in range(width):
            left, right = max(0, x - radius), min(width, x + radius + 1)
            sum_pixels = (integral[bottom * stride + right]
                          - integral[top * stride + right]
                          - integral[bottom * stride + left]
                          + integral[top * stride + left])
            out.append(sum_pixels / ((bottom - top) * (right - left)))
    return out


def preprocess_samples(samples: tuple[int, ...], *, width: int = WIDTH,
                       height: int = HEIGHT) -> Processed:
    """Band-pass normalise image detail without learning individual fingers."""
    if width * height != PIXELS or min(width, height) < 20:
        raise ValueError('Only the known 5120-pixel geometries are accepted')
    if len(samples) != width * height:
        raise ValueError('Image must contain exactly 5120 sensor samples')
    sorted_values = sorted(samples)
    low = sorted_values[int(0.01 * (PIXELS - 1))]
    high = sorted_values[int(0.99 * (PIXELS - 1))]
    if high - low < 16:
        raise ValueError('Insufficient raw image variation for a comparison')
    scale = 1.0 / (high - low)
    levels = [min(1.0, max(0.0, (v - low) * scale)) for v in samples]
    fine = box_average(levels, 1, width=width, height=height)
    background = box_average(levels, 5, width=width, height=height)
    detail = [x - y for x, y in zip(fine, background)]
    # Centre and normalise on the interior, avoiding variable edge borders.
    margin = 6
    interior = [detail[y * width + x]
                for y in range(margin, height - margin)
                for x in range(margin, width - margin)]
    mean = sum(interior) / len(interior)
    rms = math.sqrt(sum((v - mean) ** 2 for v in interior) / len(interior))
    if rms < 0.003:
        raise ValueError('Very little spatial detail; a similarity score would be misleading')
    return Processed(tuple((d - mean) / rms for d in detail), rms, high - low,
                     width, height)


def load_capture(path: Path, order: str, *, layout: str = '80x64') -> Processed:
    if path.is_symlink():
        raise ValueError(f'Refusing symlinked fingerprint file: {path.name}')
    meta = path.stat()
    if not stat.S_ISREG(meta.st_mode):
        raise ValueError(f'Not a regular file: {path.name}')
    if meta.st_size != RAW_BYTES:
        raise ValueError(f'Expected {RAW_BYTES} bytes in {path.name}; got {meta.st_size}')
    if layout not in ('80x64', '64x80'):
        raise ValueError('Expected image layout 80x64 or 64x80')
    width, height = map(int, layout.split('x'))
    return preprocess_samples(decode_samples(path.read_bytes(), order),
                              width=width, height=height)


def correlation_shift(a: tuple[float, ...], b: tuple[float, ...],
                      dx: int, dy: int, margin: int = 6,
                      width: int = WIDTH, height: int = HEIGHT) -> tuple[float, int]:
    """Pearson correlation on the shared area, shifted b relative to a."""
    min_x = max(margin, margin - dx)
    max_x = min(width - margin, width - margin - dx)
    min_y = max(margin, margin - dy)
    max_y = min(height - margin, height - margin - dy)
    n = (max_x - min_x) * (max_y - min_y)
    if n < 2000:
        return -1.0, n
    sa = sb = saa = sbb = sab = 0.0
    for y in range(min_y, max_y):
        a_base = y * width
        b_base = (y + dy) * width
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
    if not 0 <= max_shift <= 14:
        raise ValueError('max_shift must be in 0..14 pixels')
    if (a.width, a.height) != (b.width, b.height):
        raise ValueError('Cannot compare different image layouts')
    best = Comparison(-1.0, 0, 0, 0)
    for dy in range(-max_shift, max_shift + 1):
        for dx in range(-max_shift, max_shift + 1):
            score, n = correlation_shift(a.data, b.data, dx, dy,
                                         width=a.width, height=a.height)
            if score > best.correlation:
                best = Comparison(score, dx, dy, n)
    return best


def recent_captures(folder: Path, count: int) -> list[Path]:
    if folder.is_symlink():
        raise ValueError('Refusing symlinked local-data directory')
    candidates = [p for p in folder.glob('fingerprint_*.raw')
                  if p.is_file() and not p.is_symlink()]
    if len(candidates) < count:
        raise ValueError(f'Need {count} .raw fingerprint captures; found {len(candidates)} in {folder}')
    ordered = sorted(candidates, key=lambda p: (p.stat().st_mtime_ns, p.name))
    return ordered[-count:]


def recent_three(folder: Path) -> list[Path]:
    """Legacy A/B/A selection; preserved for old tests and scripts."""
    return recent_captures(folder, 3)


def recent_four(folder: Path) -> list[Path]:
    """Find newest complete, clearly-labelled A1/A2/B1/B2 series."""
    files = recent_captures(folder, 4)
    expected = ('_A1.raw', '_A2.raw', '_B1.raw', '_B2.raw')
    if not all(path.name.endswith(suffix) for path, suffix in zip(files, expected)):
        raise ValueError(
            'The latest four captures are not labelled A1, A2, B1, B2 in order. '
            'Use four explicit file paths or run a complete --session capture.'
        )
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('files', metavar='RAW', nargs='*', type=Path,
                        help='three A/B/A, or four A1/A2/B1/B2, raw capture files')
    latest = parser.add_mutually_exclusive_group()
    latest.add_argument('--latest-three', action='store_true',
                        help='latest three A1/B/A2 captures (legacy)')
    latest.add_argument('--latest-four', action='store_true',
                        help='new four-capture A1/A2/B1/B2 labelled session')
    parser.add_argument('--directory', type=Path, default=Path('local-data'),
                        help='capture directory used with --latest-three or --latest-four')
    parser.add_argument('--order', choices=('big', 'little'), default='big')
    parser.add_argument('--layout', choices=('80x64', '64x80'), default='80x64',
                        help='row-major sensor layout (default 80x64)')
    parser.add_argument('--both-layouts', action='store_true',
                        help='report both 80x64 and 64x80 interpretations')
    parser.add_argument('--max-shift', type=int, choices=range(0, 15), default=6,
                        metavar='{0..14}', help='pixel translation window (default 6)')
    args = parser.parse_args()
    if (args.latest_three or args.latest_four) and args.files:
        parser.error('Use latest-three/latest-four OR explicit filenames, not both')
    if not (args.latest_three or args.latest_four) and len(args.files) not in (3, 4):
        parser.error('Provide three A/B/A or four A1/A2/B1/B2 files, or choose --latest-four')
    try:
        if args.latest_three:
            files = recent_three(args.directory)
        elif args.latest_four:
            files = recent_four(args.directory)
        else:
            files = args.files
        labels = ('A1', 'A2', 'B1', 'B2') if len(files) == 4 else ('A1', 'B', 'A2')
        print('FocalTech 2808:5955 — OFFLINE image-similarity experiment')
        print('No USB access. No fingerprint output saved, uploaded or enrolled.')
        print(f'Decoding: {args.order}-endian; maximum translation: {args.max_shift} px')
        for label, filename in zip(labels, files):
            print(f'  {label}: {filename.name}')
        layouts = ('80x64', '64x80') if args.both_layouts else (args.layout,)
        for layout in layouts:
            print(f'\nImage layout: {layout} (unverified raw arrangement)')
            samples = [load_capture(p, args.order, layout=layout) for p in files]
            for label, data in zip(labels, samples):
                print(f'  {label} detail RMS: {data.detail_rms:.4f} (diagnostic only)')
            if len(files) == 4:
                comparisons = [
                    ('A1 vs A2 (same finger A)', 0, 1),
                    ('B1 vs B2 (same finger B)', 2, 3),
                    ('A1 vs B1 (different fingers)', 0, 2),
                    ('A1 vs B2 (different fingers)', 0, 3),
                    ('A2 vs B1 (different fingers)', 1, 2),
                    ('A2 vs B2 (different fingers)', 1, 3),
                ]
            else:
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
            if len(files) == 4:
                strongest_control = max(scores[2:])
                print(f'  Same A minus strongest different-finger control: '
                      f'{scores[0] - strongest_control:+.3f}')
                print(f'  Same B minus strongest different-finger control: '
                      f'{scores[1] - strongest_control:+.3f}')
                print('Four-capture comparison is diagnostic only, not authentication.')
            else:
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
