#!/usr/bin/env python3
"""Offline x64 GS/FS segment-reference audit of the verified 5955 MOH DLL.

Disassembles the original *private* ftWbioEngineAdapter.dll on this machine.
Does not execute PE code, interact with USB, access biometric files, or save
disassembly. The small report lists counts and instruction addresses only.

Use the verified MOH DLL or the original private Windows driver ZIP.
Results are *static evidence*, not proof that any instruction is reachable.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import zipfile

from moh_engine_preflight import PIN, archive_engine

ADDRESS = re.compile(r"^\s*([0-9a-fA-F]+):\s+(.+)$")
SEGMENT = re.compile(r"\b(gs|fs)\s*:\s*", re.IGNORECASE)
DIRECT_OFFSET = re.compile(r"^\s*(?:\[\s*)?0x([0-9a-fA-F]+)\b", re.IGNORECASE)
KNOWN_X64_TEB = {
    0x08: "NtTib.StackBase",
    0x10: "NtTib.StackLimit",
    0x20: "NtTib.FiberData",
    0x30: "NtTib.Self (TEB pointer)",
    0x40: "ClientId.UniqueProcess",
    0x48: "ClientId.UniqueThread",
    0x58: "ThreadLocalStoragePointer",
    0x60: "ProcessEnvironmentBlock (PEB)",
    0x68: "LastErrorValue",
    0x6c: "CountOfOwnedCriticalSections",
    0x1480: "TlsSlots (common Win64 TEB layout)",
}
MAX_EXAMPLES = 4


def segment_reference(line: str) -> tuple[str, int | None, str] | None:
    """Return (segment, direct constant offset or None, instruction addr).

    Accepts GNU objdump Intel output with or without machine-code bytes.
    'gs:[rax+0x68]' is *dynamic*, not incorrectly called offset 0x68.
    """
    m = ADDRESS.match(line)
    if not m:
        return None
    addr, rest = m.groups()
    seg = SEGMENT.search(rest)
    if not seg:
        return None
    tail = rest[seg.end():]
    offset = DIRECT_OFFSET.match(tail)
    return (seg.group(1).lower(), int(offset.group(1), 16) if offset else None,
            "0x" + addr.lower())


def scan_stream(lines, max_examples: int = MAX_EXAMPLES):
    counts: Counter[tuple[str, int | None]] = Counter()
    examples: dict[tuple[str, int | None], list[str]] = defaultdict(list)
    for line in lines:
        reference = segment_reference(line)
        if reference is None:
            continue
        seg, offset, address = reference
        key = (seg, offset)
        counts[key] += 1
        if len(examples[key]) < max_examples:
            examples[key].append(address)
    return counts, examples


def audit_private_dll(dll: Path):
    if not dll.is_file() or dll.is_symlink():
        raise ValueError("DLL must be a regular local file, not a symlink")
    with dll.open("rb") as input_file:
        checksum = hashlib.file_digest(input_file, "sha256").hexdigest()
    if checksum != PIN:
        raise ValueError("File is not the verified 2808:5955 MOH engine (SHA256 mismatch)")

    # Stream objdump output: no huge captured disassembly and no PE execution.
    # -d disassembles executable sections only; --no-show-raw-insn keeps
    # output bounded and parseable. The local binary stays private.
    command = ["objdump", "-d", "-M", "intel", "--no-show-raw-insn", str(dll)]
    proc = subprocess.Popen(command, stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL, text=True,
                            errors="replace", bufsize=8192)
    try:
        assert proc.stdout is not None
        counts, examples = scan_stream(proc.stdout)
        status = proc.wait(timeout=30)
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
        if proc.stdout is not None:
            proc.stdout.close()
    if status:
        raise RuntimeError(f"objdump returned exit code {status}")
    return counts, examples


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dll", type=Path,
                        help="private original 7_Fingerprint-module.zip or MOH DLL")
    args = parser.parse_args()
    try:
        with tempfile.TemporaryDirectory(prefix="ft5955-moh-teb-") as tmp:
            dll = (archive_engine(args.dll, Path(tmp))
                   if args.dll.suffix.lower() == ".zip" else args.dll)
            counts, examples = audit_private_dll(dll)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError,
            zipfile.BadZipFile) as exc:
        print(f"TEB preflight failed: {exc}", file=sys.stderr)
        return 2
    print("Verified 5955 MOH DLL — OFFLINE x64 segment-reference audit")
    print("No DLL code executed; no fingerprint data accessed or stored.")
    print(f"Segment-override instructions detected: {sum(counts.values())}")
    if not counts:
        print("No direct GS/FS references found by this disassembly method.")
        print("This does NOT prove the engine avoids TEB/PEB/TLS access.")
        return 0
    def order(item):
        (segment, offset), count = item
        return segment, offset is None, offset if offset is not None else 0
    for (segment, offset), count in sorted(counts.items(), key=order):
        if offset is None:
            info = "computed/non-constant segment address; manual review required"
            label = "dynamic"
        else:
            label = f"0x{offset:04x}"
            info = (KNOWN_X64_TEB.get(offset, "unclassified offset")
                    if segment == "gs" else "FS access — requires manual review")
        addresses = ", ".join(examples[(segment, offset)])
        print(f"  {segment.upper()}:{label}  count={count}  {info}  examples={addresses}")
    print("Only direct segment references are counted: code may read a TEB")
    print("pointer through GS once and subsequently access fields indirectly.")
    print("Static disassembly cannot establish reachability or API compatibility.")
    print("Do NOT enable MOH DLL execution based on this report.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
