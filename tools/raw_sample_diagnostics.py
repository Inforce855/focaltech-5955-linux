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



def spatial_zero_summary(samples: tuple[int, ...], width: int = 64) -> dict[str, object]:
    """Describe zero-valued raw pixels by physical rows, never expose pixels.

    Only meaningful when samples are decoded LITTLE endian; width=64 is
    the strongest current (but not completely verified) sensor geometry.
    The output is aggregated statistics, NOT a fingerprint template.
    """
    if width != 64 or len(samples) != 5120:
        raise ValueError("Expected 5120 samples and 64 columns")
    rows = [samples[y * width:(y + 1) * width] for y in range(80)]
    zeros = [sum(value == 0 for value in row) for row in rows]
    leading = 0
    for count in zeros:
        if count != width:
            break
        leading += 1
    trailing = 0
    for count in reversed(zeros):
        if count != width:
            break
        trailing += 1
    bands = (zeros[:20], zeros[20:60], zeros[60:])
    band_pcts = tuple(
        100.0 * sum(band) / (len(band) * width) for band in bands
    )
    full_zero_rows = sum(count == width for count in zeros)
    # A missing quarter need not align exactly with row boundaries.
    heavily_zero_rows = sum(count >= 3 * width // 4 for count in zeros)
    return {
        "full_zero_rows": full_zero_rows,
        "leading_full_zero_rows": leading,
        "trailing_full_zero_rows": trailing,
        "mostly_zero_rows": heavily_zero_rows,
        "band_zero_pct": band_pcts,
    }


def pair_change_summary(a: tuple[int, ...], b: tuple[int, ...]) -> tuple[int, float]:
    """How many sample values differ, without printing any actual values."""
    if len(a) != 5120 or len(b) != 5120:
        raise ValueError("Expected full 5120-sample arrays")
    changed = sum(left != right for left, right in zip(a, b))
    return changed, (100.0 * changed / len(a))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('files', type=Path, nargs='*', metavar='RAW')
    parser.add_argument('--latest-four', action='store_true',
                        help='inspect latest labelled A1/A2/B1/B2 from local-data/')
    parser.add_argument('--directory', type=Path, default=Path('local-data'))
    parser.add_argument('--spatial-zeros', action='store_true',
                        help='little-endian 64x80 zero-pixel row bands and '
                             'consecutive capture differences (numbers only)')
    args = parser.parse_args()
    if args.latest_four and args.files:
        parser.error('Use --latest-four OR explicit RAW filenames')
    if not args.latest_four and not args.files:
        parser.error('Provide private RAW files or --latest-four')
    try:
        paths = recent_four(args.directory) if args.latest_four else args.files
        print('FocalTech 2808:5955 — OFFLINE signed-16-bit diagnostic')
        print('No biometric samples, images or templates will be printed or saved.')
        little_samples = []
        for path in paths:
            raw = read_private(path)
            little_samples.append(decode_samples(raw, 'little'))
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
        if args.spatial_zeros:
            print('\n64x80 geometry: ORIGINAL little-endian zero samples '
                  '(no normalisation):')
            for path, samples in zip(paths, little_samples):
                result = spatial_zero_summary(samples)
                top, middle, bottom = result['band_zero_pct']
                print(f"  {path.name}:")
                print(f"    zero % top 20 rows={top:.1f}, middle 40={middle:.1f}, "
                      f"bottom 20={bottom:.1f}")
                print(f"    completely zero rows={result['full_zero_rows']}, "
                      f"leading={result['leading_full_zero_rows']}, "
                      f"trailing={result['trailing_full_zero_rows']}, "
                      f"rows >=75% zero={result['mostly_zero_rows']}")
            if len(little_samples) == 4:
                print('  Pairwise RAW sample changes (not fingerprint matching):')
                for title, left, right in (('A1 to A2', 0, 1),
                                           ('B1 to B2', 2, 3)):
                    changed, percentage = pair_change_summary(
                        little_samples[left], little_samples[right])
                    print(f'    {title}: {changed}/5120 sample values changed '
                          f'({percentage:.1f}%).'
                          + (' EXACTLY identical buffers.' if not changed else ''))
            print('  A zero region might be sensor contact, acquisition timing, '
                  'or masking; these statistics alone cannot identify which.')
        print('\nThese figures diagnose 16-bit interpretation, not a fingerprint match.')
        return 0
    except (OSError, ValueError) as error:
        print(f'Cannot inspect private capture: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
