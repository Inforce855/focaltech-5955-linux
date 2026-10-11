#!/usr/bin/env python3
"""Private, offline statistics for FocalTech 5955 raw image sample interpretation.

Prints ONLY aggregate statistics, not samples or image data. No USB I/O,
PNG writes, template files, authentication changes or network operations.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import stat
import sys

from raw_to_png import RAW_BYTES, decode_samples


def percentile(values: list[int], fraction: float) -> int:
    return sorted(values)[int((len(values) - 1) * fraction)]


def summarise(samples: tuple[int, ...]) -> dict[str, int | float]:
    if len(samples) != RAW_BYTES // 2:
        raise ValueError('Expected 5120 samples')
    negative_count = sum(v >= 32768 for v in samples)
    corrected = [v if v < 32768 else 0 for v in samples]
    positive = [v for v in corrected if v > 0]
    return {
        'negative_pct': negative_count * 100 / len(samples),
        'zero_after_clamp_pct': corrected.count(0) * 100 / len(samples),
        'unsigned_p01': percentile(list(samples), .01),
        'unsigned_p50': percentile(list(samples), .50),
        'unsigned_p99': percentile(list(samples), .99),
        'clamped_p01': percentile(corrected, .01),
        'clamped_p50': percentile(corrected, .50),
        'clamped_p99': percentile(corrected, .99),
        'positive_distinct': len(set(positive)),
    }


def recent_four(folder: Path) -> list[Path]:
    if folder.is_symlink():
        raise ValueError('Refusing symlinked capture directory')
    files = [p for p in folder.glob('fingerprint_*.raw')
             if p.is_file() and not p.is_symlink()]
    if len(files) < 4:
        raise ValueError('Four labelled captures are required')
    ordered = sorted(files, key=lambda p: (p.stat().st_mtime_ns, p.name))[-4:]
    for path, suffix in zip(ordered, ('_A1.raw', '_A2.raw', '_B1.raw', '_B2.raw')):
        if not path.name.endswith(suffix):
            raise ValueError('Latest captures must be A1, A2, B1, B2')
    return ordered


def read_private(path: Path) -> bytes:
    if path.is_symlink():
        raise ValueError('Refusing symlinked raw files')
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_size != RAW_BYTES:
        raise ValueError(f'Expected a regular {RAW_BYTES}-byte .raw file')
    return path.read_bytes()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('files', type=Path, nargs='*', metavar='RAW')
    parser.add_argument('--latest-four', action='store_true',
                        help='inspect latest labelled A1/A2/B1/B2 from local-data/')
    parser.add_argument('--directory', type=Path, default=Path('local-data'))
    args = parser.parse_args()
    if args.latest_four and args.files:
        parser.error('Use --latest-four OR explicit RAW filenames')
    if not args.latest_four and not args.files:
        parser.error('Provide private RAW files or --latest-four')
    try:
        paths = recent_four(args.directory) if args.latest_four else args.files
        print('FocalTech 2808:5955 — OFFLINE signed-16-bit diagnostic')
        print('No biometric samples, images or templates will be printed or saved.')
        for path in paths:
            raw = read_private(path)
            print(f'\n{path.name}:')
            for order in ('big', 'little'):
                metrics = summarise(decode_samples(raw, order))
                print(f"  {order:6s}: negative={metrics['negative_pct']:5.1f}% "
                      f"zero-after-clamp={metrics['zero_after_clamp_pct']:5.1f}% "
                      f"distinct-positive={metrics['positive_distinct']}")
                print(f"          unsigned 1/50/99%: "
                      f"{metrics['unsigned_p01']}/{metrics['unsigned_p50']}/{metrics['unsigned_p99']}")
                print(f"          clamped  1/50/99%: "
                      f"{metrics['clamped_p01']}/{metrics['clamped_p50']}/{metrics['clamped_p99']}")
        print('\nThese figures diagnose 16-bit interpretation, not a fingerprint match.')
        return 0
    except (OSError, ValueError) as error:
        print(f'Cannot inspect private capture: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
