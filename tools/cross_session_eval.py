#!/usr/bin/env python3
"""Compare TWO actual FocalTech 5955 capture sessions, offline and privately.

The default session prefixes identify the two four-impression sessions from
11 October 2026 at 14:24 and 14:55. Use --swapped only when the second
session deliberately reversed which physical finger was called A/B.

Runs the independent native C v3 normalizer via the already-built CLI.
Prints only aggregate correlations, no image exports, no templates, no USB.
A score is NOT authentication; no acceptance threshold is used.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys

from fingerprint_compare import compare, preprocess_samples
from real_capture_eval import DEFAULT_CAPTURES, convert_using_native, read_private_capture

LABELS = ("A1", "A2", "B1", "B2")
LAYOUTS = {"64x80": (64, 80), "80x64": (80, 64)}
PREFIX_PATTERN = re.compile(r"\d{2}-\d{2}-\d{4}_\d{2}-\d{2}\Z")


def session_files(folder: Path, prefix: str) -> list[Path]:
    """Find exactly one complete session, independent of file modification time."""
    if not PREFIX_PATTERN.fullmatch(prefix):
        raise ValueError("Session prefix must be DD-MM-YYYY_HH-MM")
    if folder.is_symlink() or not folder.is_dir():
        raise ValueError("Capture directory must be an ordinary local directory")

    names = {}
    filename = re.compile(
        r"fingerprint_" + re.escape(prefix) + r"-\d{2}_(A1|A2|B1|B2)\.raw\Z"
    )
    for path in folder.glob(f"fingerprint_{prefix}-*.raw"):
        result = filename.fullmatch(path.name)
        if result:
            label = result.group(1)
            if label in names:
                raise ValueError(
                    f"More than one {label} capture for session {prefix}"
                )
            if path.is_symlink():
                raise ValueError("Refusing symlinked fingerprint captures")
            names[label] = path

    missing = [label for label in LABELS if label not in names]
    if missing:
        raise ValueError(
            f"Incomplete session {prefix}: missing {', '.join(missing)}"
        )
    return [names[label] for label in LABELS]


def is_same_physical_finger(earlier_index: int, later_index: int,
                            *, swapped: bool) -> bool:
    """Identity labels are supplied by the operator, NEVER inferred from scores."""
    early_group = earlier_index // 2
    late_group = later_index // 2
    return (early_group != late_group) if swapped else (
        early_group == late_group
    )


def score_sessions(early: list[bytes], late: list[bytes], *,
                   width: int, height: int, swapped: bool):
    """Return 16 paired score records; only the existing exploratory scorer."""
    prepped_early = [
        preprocess_samples(tuple(im), width=width, height=height)
        for im in early
    ]
    prepped_late = [
        preprocess_samples(tuple(im), width=width, height=height)
        for im in late
    ]
    results = []
    for ei, a in enumerate(prepped_early):
        for li, b in enumerate(prepped_late):
            r = compare(a, b, max_shift=6)
            results.append((
                ei, li, is_same_physical_finger(ei, li, swapped=swapped),
                r.correlation, r.dx, r.dy
            ))
    return results


def summarize(records) -> None:
    genuine = [r[3] for r in records if r[2]]
    different = [r[3] for r in records if not r[2]]
    if len(genuine) != 8 or len(different) != 8:
        raise ValueError("Expected eight genuine and eight control comparisons")
    greatest_different = max(different)
    least_genuine = min(genuine)
    genuine_above = sum(score > greatest_different for score in genuine)
    edge = sum(abs(dx) == 6 or abs(dy) == 6
               for _, _, _, _, dx, dy in records)
    print("  Early capture vs late capture (G=same physical finger, D=different):")
    print("                       late A1     late A2     late B1     late B2")
    for ei in range(4):
        row = [r for r in records if r[0] == ei]
        cells = "  ".join(f"{r[3]:+.3f}{'G' if r[2] else 'D'}"
                          for r in row)
        print(f"  early {LABELS[ei]:<2}            {cells}")
    print(f"  Genuine scores:   mean={sum(genuine)/8:+.3f}, "
          f"min={least_genuine:+.3f}, max={max(genuine):+.3f}")
    print(f"  Different scores: mean={sum(different)/8:+.3f}, "
          f"min={min(different):+.3f}, max={greatest_different:+.3f}")
    print(f"  Strict separation (min genuine minus max different): "
          f"{least_genuine - greatest_different:+.3f}")
    print(f"  Genuine pairs beating EVERY different-finger control: "
          f"{genuine_above}/8")
    print(f"  Best shifts hitting +/-6 pixel boundary: {edge}/16")
    print("  Not authentication, not a match threshold, not a security decision.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--earlier", default="11-10-2026_14-24",
                        help="first four-capture session, DD-MM-YYYY_HH-MM")
    parser.add_argument("--later", default="11-10-2026_14-55",
                        help="second four-capture session, DD-MM-YYYY_HH-MM")
    parser.add_argument("--swapped", action="store_true",
                        help="the second session reversed physical A/B fingers")
    parser.add_argument("--directory", type=Path, default=DEFAULT_CAPTURES,
                        help="private gitignored capture directory")
    args = parser.parse_args()

    try:
        if args.earlier == args.later:
            raise ValueError("Sessions must be different")
        old_files = session_files(args.directory, args.earlier)
        new_files = session_files(args.directory, args.later)
        old_bytes = [convert_using_native(read_private_capture(p))
                     for p in old_files]
        new_bytes = [convert_using_native(read_private_capture(p))
                     for p in new_files]
        print("FocalTech 5955 cross-session REAL-CAPTURE diagnostic")
        print("Offline only; no PNGs saved; native C v3 + exploratory correlation.")
        print(f"Earlier {args.earlier}: " +
              ", ".join(p.name for p in old_files))
        print(f"Later   {args.later}: " +
              ", ".join(p.name for p in new_files))
        print("ASSUMED finger labels: " + (
            "physical A/B swapped between sessions" if args.swapped
            else "physical A/B unchanged between sessions"
        ))
        for name, (width, height) in LAYOUTS.items():
            print(f"\nLayout {name}:")
            records = score_sessions(old_bytes, new_bytes, width=width,
                                     height=height, swapped=args.swapped)
            summarize(records)
        print("\nOnly aggregate scores may be shared. "
              "Real biometric images remain private on this computer.")
        return 0
    except (OSError, ValueError, RuntimeError) as error:
        print(f"Cross-session diagnostic failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
