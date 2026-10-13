#!/usr/bin/env python3
"""Offline A/B: one private Windows FocalTech BIR, two WinBio record layouts.

The same 64x80 vendor pixel payload is presented in (A) the original Windows
BIR unchanged and (B) the Linux harness's synthetic BIR. This isolates
record-layout differences without new scans, Windows VM, network or USB.
Runs separately inside the existing isolated bubblewrap DLL harness.

No templates or biometric image bytes are printed, saved or uploaded.
No enrollment commit is performed. One capture cannot establish completion.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import stat
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
RUNNER = ROOT / "tools/test_moh_isolated_pgm_enroll_batch.sh"


def field(pattern: str, data: str) -> str:
    match = re.search(pattern, data, re.IGNORECASE)
    return match.group(1) if match else "unavailable"


def inspect_private_bir(path: Path) -> None:
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_size != 5256 or path.suffix.lower() != ".bir":
        raise ValueError("Expected one regular 5256-byte local Windows .bir file")
    with path.open("rb") as inp:
        prefix = inp.read(140)
    if len(prefix) != 140 or struct.unpack("<8I", prefix[:32]) != (
        48, 32, 40, 80, 5136, 120, 0, 0
    ):
        raise ValueError("Windows BIR block offsets/sizes do not match our observed capture")
    if prefix[32 + 4] & 2:
        raise ValueError("Windows BIR indicates encrypted data; refusing comparison")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("archive", type=Path, help="Local original vendor ZIP")
    ap.add_argument("bir", type=Path, help="Local private Windows .bir, never upload")
    args = ap.parse_args()
    if not args.archive.is_file():
        ap.error("Driver ZIP not found")
    try:
        inspect_private_bir(args.bir)
    except (OSError, ValueError) as e:
        ap.error(str(e))
    print("Same single Windows capture; comparing BIR layout only.")
    print("No new scans, USB, Windows VM, template commit or biometric output.")
    print("Direct: genuine Windows BIR unchanged.")
    print("Synthetic: identical Windows vendor pixels in the existing Linux BIR wrapper.")
    print()
    print("Mode                 Accept HR    Quality   Area    Update HR    Status HR")
    print("-" * 76)
    ok = True
    for mode, opt in (
        ("Windows BIR direct", "--windows-bir-direct"),
        ("Linux BIR synthetic", "--windows-bir-synthetic"),
    ):
        try:
            proc = subprocess.run(
                ["bash", str(RUNNER), opt, str(args.archive.resolve()),
                 str(args.bir.resolve())],
                cwd=ROOT, text=True, capture_output=True, timeout=120, check=False,
            )
        except subprocess.TimeoutExpired:
            print(f"{mode:<21} TIMED OUT")
            ok = False
            continue
        if proc.returncode:
            print(f"{mode:<21} isolated runner failed (exit {proc.returncode})")
            ok = False
            continue
        log = proc.stderr
        accept = field(r"AcceptSampleData HRESULT:\s*0x([a-f0-9]{8})", log)
        quality = field(r"focal_SendImageAndGetQualityAreaCond\.\.\.quality = (\d+)", log)
        area = field(r"focal_SendImageAndGetQualityAreaCond\.\.\.quality = \d+, area = (\d+)", log)
        update = field(r"ENROLL_DIAG update_hr=0x([a-f0-9]{8})", log)
        status = field(r"ENROLL_DIAG status_hr=0x([a-f0-9]{8})", log)
        print(f"{mode:<21} {('0x'+accept) if accept!='unavailable' else '-':<12}"
              f" {quality:>7} {area:>6}"
              f" {('0x'+update) if update!='unavailable' else '-':>12}"
              f" {('0x'+status) if status!='unavailable' else '-':>12}")
        if accept == "unavailable":
            ok = False
    print()
    print("This is a one-sample FORMAT comparison, not an enrollment completion test.")
    print("No biometric template was saved or committed.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
