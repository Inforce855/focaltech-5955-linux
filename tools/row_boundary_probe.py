#!/usr/bin/env python3
"""OFFLINE row-boundary diagnostics for private FocalTech 2808:5955 raw frames.

Examines discontinuities in a *1-D* sequence of 5,120 little-endian words,
hypothesising that true row boundaries fall every 64 or 80 samples.

No USB, PNG output, stored features/templates, network or authentication.
Prints aggregate statistics only; actual biometric samples stay private.
A strong seam signal is a clue, NOT proof of physical image geometry.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from statistics import median
import sys

from raw_sample_diagnostics import read_private, recent_four
from raw_to_png import decode_samples, PIXELS


def quantile(values: list[int], fraction: float) -> float:
    if not values:
        raise ValueError("Cannot compute quantile of empty differences")
    return float(sorted(values)[int((len(values) - 1) * fraction)])


def seam_statistics(samples: tuple[int, ...], width: int) -> dict[str, float | int]:
    """Quantify jumps at candidate row wraps vs ordinary adjacent samples.

    The difference between last and first samples of consecutive rows is
    normally NOT spatially local. If width is right, these boundary jumps
    can be larger than horizontal within-row steps. However noise, zeros,
    line-specific sensor biases and real ridge orientation can confound it.
    """
    if len(samples) != PIXELS or width not in (64, 80):
        raise ValueError("Expected 5120 samples and a 64/80-pixel row width")
    differences = [abs(a - b) for a, b in zip(samples[:-1], samples[1:])]
    inside = [d for i, d in enumerate(differences) if (i + 1) % width != 0]
    seams = [d for i, d in enumerate(differences) if (i + 1) % width == 0]
    if not inside or not seams:
        raise ValueError("Missing row seams or within-row samples")
    inside_median = float(median(inside))
    seams_median = float(median(seams))
    inside_p90 = quantile(inside, .90)
    significant_seams = 100 * sum(d > inside_p90 for d in seams) / len(seams)

    local_fold = []
    for k in range(width - 1, len(differences), width):
        nearby = [differences[j] for j in range(max(0, k - 8), min(len(differences), k + 9))
                  if j != k and (j + 1) % width != 0]
        if nearby:
            local_fold.append((differences[k] + 1) / (median(nearby) + 1))
    vertical_deltas = [abs(a - b) for a, b in zip(samples[:-width], samples[width:])]
    return {
        "rows": PIXELS // width,
        "seams": len(seams),
        "within_median": inside_median,
        "seam_median": seams_median,
        "seam_over_within": (seams_median + 1) / (inside_median + 1),
        "seams_over_p90_pct": significant_seams,
        "local_seam_fold_median": float(median(local_fold)),
        "vertical_median": float(median(vertical_deltas)),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", type=Path, nargs="*", metavar="RAW",
                        help="private 10240-byte captures to inspect")
    parser.add_argument("--latest-four", action="store_true",
                        help="use latest complete A1 A2 B1 B2 capture set")
    parser.add_argument("--directory", type=Path, default=Path("local-data"))
    args = parser.parse_args()
    if args.latest_four and args.files:
        parser.error("Choose --latest-four OR explicit RAW files")
    if not args.latest_four and not args.files:
        parser.error("Provide private RAW files or --latest-four")
    try:
        files = recent_four(args.directory) if args.latest_four else args.files
        print("FocalTech 2808:5955 — OFFLINE candidate row-boundary diagnostic")
        print("Input: LITTLE-endian original 16-bit sensor samples")
        print("No USB, output files or biometric sample values printed/saved.")
        print("A seam is a consecutive-sample jump at a proposed row boundary.")
        for filename in files:
            samples = decode_samples(read_private(filename), "little")
            print(f"\n{filename.name}:")
            for width in (64, 80):
                s = seam_statistics(samples, width)
                print(f"  width {width} ({s['rows']} rows, {s['seams']} seams):")
                print(f"    median jump within={s['within_median']:.1f}, "
                      f"at seam={s['seam_median']:.1f}, "
                      f"seam/within={s['seam_over_within']:.2f}x")
                print(f"    seams above within-row 90th percentile: "
                      f"{s['seams_over_p90_pct']:.1f}%")
                print(f"    median seam/local jump ratio: "
                      f"{s['local_seam_fold_median']:.2f}x")
                print(f"    median vertical-neighbour jump: "
                      f"{s['vertical_median']:.1f}")
        print("\nThese are shape hypotheses, not verified ridges or fingerprints.")
        print("Sensor-specific row patterns and empty edges can bias the test.")
        return 0
    except (OSError, ValueError) as error:
        print(f"Unable to inspect local capture: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
