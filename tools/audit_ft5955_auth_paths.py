#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Read-only trust-boundary audit for proposed system-owned MOH deployment.

Only evaluates filesystem ownership and writable ancestor paths; it neither
enables authentication nor claims that the proprietary engine is safe.
"""
import argparse
import os
from pathlib import Path
import stat
import sys


def audit_path(path: Path, *, expected_uid: int = 0, kind: str = "file") -> list[str]:
    failures = []
    if not path.is_absolute():
        return ["path is not absolute"]
    current = Path("/")
    parts = path.parts[1:]
    for index, part in enumerate(parts):
        current = current / part
        try:
            info = current.lstat()
        except OSError as exc:
            failures.append(f"{current}: {type(exc).__name__}")
            break
        if stat.S_ISLNK(info.st_mode):
            failures.append(f"{current}: symlink in trusted path")
            break
        if info.st_uid != expected_uid:
            failures.append(f"{current}: owner uid {info.st_uid}, expected {expected_uid}")
        if info.st_mode & 0o022:
            failures.append(f"{current}: group/other writable")
        last = index == len(parts) - 1
        if not last and not stat.S_ISDIR(info.st_mode):
            failures.append(f"{current}: ancestor is not a directory")
            break
        if last and not (stat.S_ISREG(info.st_mode) if kind == "file" else stat.S_ISDIR(info.st_mode)):
            failures.append(f"{current}: not a regular {kind}")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gateway", type=Path, required=True,
                        help="proposed root-owned gateway source")
    parser.add_argument("--broker", type=Path, required=True,
                        help="proposed root-owned broker executable")
    parser.add_argument("--moh-dir", type=Path, required=True,
                        help="proposed root-owned MOH runner directory")
    parser.add_argument("--dll", type=Path, required=True,
                        help="proposed root-owned pinned MOH DLL")
    args = parser.parse_args()
    failed = False
    for label, path, kind in (
        ("GATEWAY", args.gateway, "file"),
        ("BROKER", args.broker, "file"),
        ("MOH", args.moh_dir, "dir"),
        ("DLL", args.dll, "file"),
    ):
        issues = audit_path(path, kind=kind)
        print(f"{label}: {'FAIL' if issues else 'PASS'} {path}")
        for issue in issues:
            print(f"  {issue}")
        failed |= bool(issues)
    print("MOH TRUST-BOUNDARY CHECK:", "FAIL" if failed else "PATHS PASS (not authentication approval)")
    print("This does not audit service UID, runtime isolation, templates, DLL ABI or biometric security.")
    return int(failed)


if __name__ == "__main__":
    sys.exit(main())
