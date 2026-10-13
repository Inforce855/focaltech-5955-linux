#!/usr/bin/env python3
"""Verify private MOH SHA then run the native, read-only PE bounds guard.

Uses a fresh temporary work directory for the extracted DLL and standalone
C test executable. Does not execute, load or link the proprietary PE DLL.
"""
from __future__ import annotations
import argparse
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile
from moh_engine_preflight import PIN, archive_engine


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("dll", type=Path, help="original 7_Fingerprint-module.zip or private MOH DLL")
    args = p.parse_args()
    root = Path(__file__).resolve().parents[1]
    try:
        with tempfile.TemporaryDirectory(prefix="ft5955-pe-guard-") as tmp:
            directory = Path(tmp)
            dll = (archive_engine(args.dll, directory)
                   if args.dll.suffix.lower() == ".zip" else args.dll)
            if not dll.is_file() or dll.is_symlink():
                raise ValueError("Private MOH DLL must be a regular non-symlink file")
            if hashlib.sha256(dll.read_bytes()).hexdigest() != PIN:
                raise ValueError("Private MOH DLL SHA256 mismatch")
            exe = directory / "moh_pe_guard_check"
            subprocess.run([
                "cc", "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
                "-I", str(root / "engine"),
                str(root / "engine" / "ft5955_pe_guard.c"),
                str(root / "engine" / "ft5955_pe_exports.c"),
                str(root / "tools" / "moh_pe_guard_check.c"),
                "-o", str(exe),
            ], check=True)
            status = subprocess.run([str(exe), str(dll)], check=False)
            return status.returncode
    except (OSError, ValueError, subprocess.SubprocessError,
            zipfile.BadZipFile) as exc:
        print(f"5955 offline PE guard probe failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
