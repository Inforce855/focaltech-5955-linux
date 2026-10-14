#!/usr/bin/env python3
"""Offline, bounded instruction context for GS/FS references in the 5955 MOH DLL.

Reads only the original SHA256-verified private MOH DLL (or its original ZIP).
Does not execute the DLL, read fingerprints, or save disassembly.
Prints short *local* instruction excerpts to investigate TEB pointer derefs.
Do not publish this output as a full disassembly.
"""
from __future__ import annotations

import argparse
from collections import deque
import hashlib
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import zipfile

from moh_engine_preflight import PIN, archive_engine
from moh_teb_audit import ADDRESS, segment_reference

FUNC_HEADING = re.compile(r"^[0-9a-fA-F]+\s+<[^>]+>:\s*$")


def find_contexts(lines, before: int = 3, after: int = 9, limit: int = 16):
    """Return (total hits, list of bounded context records) in one streaming pass.

    Nearby GS hits intentionally have overlapping windows. Never merge them
    into an invented data-flow interpretation. Reset at function boundaries.
    """
    previous = deque(maxlen=before)
    contexts = []
    active = []
    total = 0
    for raw in lines:
        line = raw.strip()
        if FUNC_HEADING.match(line):
            previous.clear()
            active.clear()
            continue
        if not ADDRESS.match(line):
            continue
        # Existing windows receive THIS instruction before adding a new one.
        for item in active[:]:
            if len(item["after"]) < after:
                item["after"].append(line)
            if len(item["after"]) == after:
                active.remove(item)
        reference = segment_reference(line)
        if reference:
            total += 1
            if len(contexts) < limit:
                segment, offset, address = reference
                item = {
                    "segment": segment,
                    "offset": offset,
                    "address": address,
                    "before": list(previous),
                    "hit": line,
                    "after": [],
                }
                contexts.append(item)
                if after:
                    active.append(item)
        previous.append(line)
    return total, contexts


def inspect_private_engine(path: Path, before: int, after: int, limit: int):
    if not path.is_file() or path.is_symlink():
        raise ValueError("MOH DLL must be a regular local file, not a symlink")
    with path.open("rb") as f:
        digest = hashlib.file_digest(f, "sha256").hexdigest()
    if digest != PIN:
        raise ValueError("Engine DLL does not match pinned FocalTech 5955 MOH SHA256")

    argv = ["objdump", "-d", "-M", "intel", "--no-show-raw-insn", str(path)]
    proc = subprocess.Popen(argv, stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL, text=True,
                            errors="replace", bufsize=8192)
    try:
        if proc.stdout is None:
            raise RuntimeError("objdump stdout unavailable")
        total, contexts = find_contexts(proc.stdout, before, after, limit)
        status = proc.wait(timeout=30)
        if status:
            raise RuntimeError(f"objdump returned exit code {status}")
        return total, contexts
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
        if proc.stdout is not None:
            proc.stdout.close()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("dll", type=Path, help="original private MOH DLL or Windows driver ZIP")
    p.add_argument("--before", type=int, default=3, choices=range(0, 7),
                   metavar="0..6", help="preceding instructions per hit (default: 3)")
    p.add_argument("--after", type=int, default=9, choices=range(1, 17),
                   metavar="1..16", help="following instructions per hit (default: 9)")
    p.add_argument("--limit", type=int, default=16, choices=range(1, 33),
                   metavar="1..32", help="max contexts printed (default: 16)")
    args = p.parse_args()
    try:
        with tempfile.TemporaryDirectory(prefix="ft5955-moh-context-") as d:
            dll = (archive_engine(args.dll, Path(d))
                   if args.dll.suffix.lower() == ".zip" else args.dll)
            total, contexts = inspect_private_engine(dll, args.before,
                                                      args.after, args.limit)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError,
            zipfile.BadZipFile) as exc:
        print(f"TEB context inspection failed: {exc}", file=sys.stderr)
        return 2

    print("Verified 5955 MOH DLL — local-only GS/FS instruction contexts")
    print("No vendor DLL code executed; no biometric files read or stored.")
    print(f"Detected {total} segment overrides; showing {len(contexts)} contexts.")
    for i, item in enumerate(contexts, 1):
        offset = (f"0x{item['offset']:x}" if item["offset"] is not None
                  else "dynamic")
        print(f"\n[{i}] {item['segment'].upper()}:{offset} at {item['address']}")
        for line in item["before"]:
            print("   " + line)
        print(" > " + item["hit"])
        for line in item["after"]:
            print("   " + line)
    print("\nStatic instruction windows only: a register may be overwritten or")
    print("aliased outside the window; no indirect TEB field use is proved.")
    print("DLL execution and fprintd/PAM remain disabled.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
