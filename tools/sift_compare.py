#!/usr/bin/env python3
"""OFFLINE exploratory SIFT comparison for private FocalTech 2808:5955 captures.

Independently implemented with standard OpenCV methods, inspired by the
published architecture at scamiran149/libfprint_focaltechc652 (2808:c652).
Neither its USB driver nor its template serializer is imported or installed.

No USB I/O, files created, templates saved, enrollment, authentication, or
network calls. Prints aggregate keypoint/match counts only. These counts are
NOT a validated fingerprint matcher or access-control decision.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import stat
import sys

from fingerprint_compare import recent_four
from raw_to_png import RAW_BYTES

LAYOUTS = {"80x64": (80, 64), "64x80": (64, 80)}
PAIRS = (
    ("A1 ↔ A2 (same A)", 0, 1),
    ("B1 ↔ B2 (same B)", 2, 3),
    ("A1 ↔ B1 (different)", 0, 2),
    ("A1 ↔ B2 (different)", 0, 3),
    ("A2 ↔ B1 (different)", 1, 2),
    ("A2 ↔ B2 (different)", 1, 3),
)


def dependencies():
    try:
        import numpy as np
        import cv2
    except ImportError as err:
        raise RuntimeError(
            "Optional OpenCV dependency missing. Install into this project venv "
            "with: .venv/bin/python -m pip install opencv-python-headless"
        ) from err
    if not hasattr(cv2, "SIFT_create"):
        raise RuntimeError("This OpenCV build does not provide SIFT_create")
    return np, cv2


def safe_raw(path: Path) -> bytes:
    if path.is_symlink():
        raise ValueError("Refusing symlinked biometric input")
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_size != RAW_BYTES:
        raise ValueError(f"Capture {path.name} is not a regular {RAW_BYTES}-byte file")
    return path.read_bytes()


def enhance(raw: bytes, width: int, height: int, np, cv2):
    """Small image -> bicubic -> bilateral -> background subtraction -> CLAHE.

    An experimental adaptation of publicly described image-processing steps.
    It does NOT reproduce the MOH Windows conversion function and may
    amplify sensor artefacts. Tenfold enlargement creates no new information.
    """
    if len(raw) != RAW_BYTES or (width, height) not in LAYOUTS.values():
        raise ValueError("Expected 5120 little-endian 16-bit samples in known geometry")
    source = np.frombuffer(raw, dtype="<u2").reshape(height, width).astype(np.float32)
    enlarged = cv2.resize(source, (width * 10, height * 10),
                          interpolation=cv2.INTER_CUBIC)
    cleaned = cv2.bilateralFilter(enlarged, 7, 50, 50)
    background = cv2.boxFilter(cleaned, cv2.CV_32F, (31, 31))
    details = cleaned - background
    low = float(details.min())
    high = float(details.max())
    if high - low < 1e-6:
        output = np.zeros(details.shape, dtype=np.uint8)
    else:
        output = np.clip((details - low) * (255.0 / (high - low)), 0, 255)
        output = output.astype(np.uint8)
    clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(8, 8))
    return clahe.apply(output)


def extract_features(enhanced, cv2):
    sift = cv2.SIFT_create()
    keypoints, descriptors = sift.detectAndCompute(enhanced, None)
    return keypoints, descriptors


def score_pair(a, b, np, cv2):
    """Count ratio-filtered SIFT matches and RANSAC homography inliers.

    No threshold is applied or proposed; degenerate geometry returns 0.
    """
    keypoints_a, descriptors_a = a
    keypoints_b, descriptors_b = b
    if descriptors_a is None or descriptors_b is None:
        return 0, 0
    if len(descriptors_a) < 2 or len(descriptors_b) < 2:
        return 0, 0
    matcher = cv2.BFMatcher(cv2.NORM_L2)
    matches = matcher.knnMatch(descriptors_a, descriptors_b, k=2)
    good = [pair[0] for pair in matches
            if len(pair) == 2 and pair[0].distance < 0.8 * pair[1].distance]
    if len(good) < 4:
        return len(good), 0
    src = np.float32([keypoints_a[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
    dst = np.float32([keypoints_b[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
    try:
        transform, mask = cv2.findHomography(src, dst, cv2.RANSAC, 5.0)
    except cv2.error:
        return len(good), 0
    if transform is None or mask is None:
        return len(good), 0
    return len(good), int(mask.sum())


def experiment(files: list[Path], layout: str, np, cv2):
    width, height = LAYOUTS[layout]
    features = []
    for path in files:
        enhanced = enhance(safe_raw(path), width, height, np, cv2)
        features.append(extract_features(enhanced, cv2))
    print(f"\nLayout {layout} — OpenCV SIFT experimental diagnostic:")
    for label, (points, _) in zip(("A1", "A2", "B1", "B2"), features):
        print(f"  {label} keypoints: {len(points)}")
    for description, i, j in PAIRS:
        matches, inliers = score_pair(features[i], features[j], np, cv2)
        print(f"  {description}: ratio matches={matches}, RANSAC inliers={inliers}")
    print("  Inliers are NOT an identity decision or security threshold.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", type=Path, nargs="*", metavar="RAW",
                        help="optional four private files in A1 A2 B1 B2 order")
    parser.add_argument("--latest-four", action="store_true",
                        help="use latest labelled A1 A2 B1 B2 files in local-data/")
    parser.add_argument("--directory", type=Path, default=Path("local-data"))
    parser.add_argument("--layout", choices=("80x64", "64x80", "both"), default="both")
    args = parser.parse_args()
    if args.latest_four and args.files:
        parser.error("Choose --latest-four OR explicit files, not both")
    if not args.latest_four and len(args.files) != 4:
        parser.error("Provide exactly four private RAW paths, or --latest-four")
    try:
        paths = recent_four(args.directory) if args.latest_four else args.files
        np, cv2 = dependencies()
        print("FocalTech 2808:5955 — OFFLINE OpenCV SIFT experiment")
        print("No USB access; no biometric images, descriptors or templates saved.")
        print("Byte order: little; input: four original raw captures (A1 A2 B1 B2).")
        for label, path in zip(("A1", "A2", "B1", "B2"), paths):
            print(f"  {label}: {path.name}")
        for layout in (("80x64", "64x80") if args.layout == "both" else (args.layout,)):
            experiment(paths, layout, np, cv2)
        print("\nNo validated match threshold; don't use results for login.")
        return 0
    except (OSError, ValueError, RuntimeError) as error:
        print(f"Offline SIFT diagnostic failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
