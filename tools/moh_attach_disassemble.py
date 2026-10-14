#!/usr/bin/env python3
"""Disassemble the pinned MOH EngineInterface::Attach entry point offline.

Reads only the SHA256-pinned DLL from the supplied vendor ZIP. No execution,
USB communication, enrolment, fingerprint samples, or persistent DLL copy.
The RVA is from the verified 41-slot interface inspection (slot 0).
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import re
import subprocess
import sys
import tempfile

from moh_engine_preflight import PIN, archive_engine

IMAGE_BASE = 0x180000000
ATTACH_RVA = 0x128D20
MAX_BYTES = 0x1000

def inspect(dll: Path, length: int) -> int:
    if not dll.is_file():
        raise ValueError("DLL is not a regular file")
    with dll.open("rb") as handle:
        digest = hashlib.file_digest(handle, "sha256").hexdigest()
    if digest != PIN:
        raise ValueError("MOH DLL hash mismatch — refusing to inspect")
    start = IMAGE_BASE + ATTACH_RVA
    end = start + length
    command = [
        "objdump", "-d", "-M", "intel",
        f"--start-address={start}", f"--stop-address={end}", str(dll),
    ]
    result = subprocess.run(command, capture_output=True, text=True,
                            check=True, timeout=30)
    lines = result.stdout.splitlines()
    instructions = [line for line in lines if re.match(r"^\s*[0-9a-f]+:\s", line)]
    if not instructions:
        raise ValueError("No disassembly produced at expected Attach RVA")
    print(f"Verified pinned engine: SHA256 {PIN}")
    print(f"Interface slot 0 (Attach): RVA 0x{ATTACH_RVA:x}")
    print("DISASSEMBLY ONLY — Windows x64 first argument is RCX (pipeline pointer)")
    print("Look for [rcx+offset] references and any called functions that")
    print("dereference pipeline/sensor/storage structures.")
    print()
    for line in instructions:
        print(line)
    print()
    print(f"Displayed {len(instructions)} instructions within first {length} bytes.")
    print("Do not enable FT5955_ALLOW_UNVERIFIED_ATTACH from this result alone.")
    return 0

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path, help="Private MOH driver ZIP or DLL")
    parser.add_argument("--bytes", type=lambda x: int(x, 0), default=0x800,
                        help="Disassembly window, 0x40 to 0x1000 (default 0x800)")
    args = parser.parse_args()
    if not 0x40 <= args.bytes <= MAX_BYTES:
        parser.error("--bytes must be between 0x40 and 0x1000")
    try:
        if args.archive.suffix.lower() == ".zip":
            with tempfile.TemporaryDirectory(prefix="ft5955-disasm-") as temp:
                dll = archive_engine(args.archive, Path(temp))
                return inspect(dll, args.bytes)
        return inspect(args.archive, args.bytes)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"BLOCKED: {error}", file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
