#!/usr/bin/env python3
"""Read-only PE32+ TLS directory and callback metadata audit for the pinned MOH DLL.

Accepts the verified, private 2808:5955 MOH engine DLL or the original ZIP.
Never executes any code, invokes callbacks, opens USB, reads fingerprints or
stores PE disassembly. Output is limited to PE metadata and callback addresses.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import struct
import sys
import tempfile
import zipfile

from moh_engine_preflight import PIN, archive_engine

MAX_SECTIONS = 96
MAX_CALLBACKS = 32


def unpack(data: bytes, offset: int, fmt: str):
    size = struct.calcsize(fmt)
    if offset < 0 or offset + size > len(data):
        raise ValueError("PE field extends outside the input file")
    return struct.unpack_from(fmt, data, offset)[0]


def u16(data, offset):
    return unpack(data, offset, "<H")


def u32(data, offset):
    return unpack(data, offset, "<I")


def u64(data, offset):
    return unpack(data, offset, "<Q")


class PeImage:
    def __init__(self, data: bytes):
        self.data = data
        if len(data) < 0x100 or data[:2] != b"MZ":
            raise ValueError("Not a DOS/PE executable")
        nt = u32(data, 0x3c)
        if nt + 24 > len(data) or data[nt:nt + 4] != b"PE\x00\x00":
            raise ValueError("Invalid PE header")
        num_sections = u16(data, nt + 6)
        opt_size = u16(data, nt + 20)
        if num_sections > MAX_SECTIONS or not num_sections:
            raise ValueError("Invalid PE section count")
        opt = nt + 24
        if opt + opt_size > len(data) or opt_size < 112:
            raise ValueError("Truncated PE32+ optional header")
        if u16(data, opt) != 0x20b:
            raise ValueError("Only x64 PE32+ files are supported")
        self.image_base = u64(data, opt + 24)
        self.size_image = u32(data, opt + 56)
        self.size_headers = u32(data, opt + 60)
        self.num_dirs = u32(data, opt + 108)
        if not self.size_image or not self.size_headers:
            raise ValueError("Invalid PE image/header size")
        self.opt = opt
        self.opt_size = opt_size
        sections_at = opt + opt_size
        if sections_at + 40 * num_sections > len(data):
            raise ValueError("Truncated PE section table")
        self.sections = []
        for i in range(num_sections):
            at = sections_at + i * 40
            vaddr = u32(data, at + 12)
            rawsize = u32(data, at + 16)
            rawptr = u32(data, at + 20)
            if rawsize and (rawptr > len(data) or rawsize > len(data) - rawptr):
                raise ValueError("PE section raw data extends beyond the file")
            self.sections.append((vaddr, rawsize, rawptr))

    def offset(self, rva: int, length: int = 1) -> int:
        if length < 0 or rva < 0 or rva + length > self.size_image:
            raise ValueError("RVA outside declared PE image")
        if rva < self.size_headers and rva + length <= self.size_headers:
            if rva + length > len(self.data):
                raise ValueError("PE headers truncated")
            return rva
        for vaddr, rawsize, rawptr in self.sections:
            if vaddr <= rva and rva - vaddr + length <= rawsize:
                at = rawptr + rva - vaddr
                if at + length > len(self.data):
                    raise ValueError("Section raw data truncated")
                return at
        raise ValueError(f"RVA 0x{rva:x} is not fully present in raw PE data")

    def va_to_rva(self, va: int) -> int:
        if va < self.image_base or va - self.image_base >= self.size_image:
            raise ValueError("TLS VA is outside the preferred image")
        return va - self.image_base

    def parse_tls(self):
        if self.num_dirs < 10:
            return None
        entry = self.opt + 112 + 9 * 8
        if entry + 8 > self.opt + self.opt_size:
            raise ValueError("PE optional header truncates TLS data directory")
        directory_rva = u32(self.data, entry)
        directory_size = u32(self.data, entry + 4)
        if not directory_rva and not directory_size:
            return None
        if directory_rva == 0 or directory_size < 40:
            raise ValueError("TLS directory is missing/truncated")
        tls_at = self.offset(directory_rva, 40)
        raw_start = u64(self.data, tls_at)
        raw_end = u64(self.data, tls_at + 8)
        index_va = u64(self.data, tls_at + 16)
        callbacks_va = u64(self.data, tls_at + 24)
        zero_fill = u32(self.data, tls_at + 32)
        characteristics = u32(self.data, tls_at + 36)
        if raw_end < raw_start:
            raise ValueError("TLS template end precedes its start")
        length = raw_end - raw_start
        if length > 16 * 1024 * 1024:
            raise ValueError("Excessively large TLS template")
        if length:
            self.offset(self.va_to_rva(raw_start), length)
        if index_va:
            self.offset(self.va_to_rva(index_va), 4)
        callbacks = []
        if callbacks_va:
            table_rva = self.va_to_rva(callbacks_va)
            for i in range(MAX_CALLBACKS + 1):
                value = u64(self.data, self.offset(table_rva + i * 8, 8))
                if value == 0:
                    break
                if i == MAX_CALLBACKS:
                    raise ValueError("TLS callback table exceeds 32 entries")
                self.va_to_rva(value)
                callbacks.append(value)
            else:
                raise ValueError("TLS callback array lacks a NULL terminator")
        return {
            "tls_rva": directory_rva,
            "template_bytes": length,
            "zero_fill_bytes": zero_fill,
            "index_va": index_va,
            "callbacks_va": callbacks_va,
            "callbacks": callbacks,
            "characteristics": characteristics,
        }


def audit_file(path: Path):
    if not path.is_file() or path.is_symlink():
        raise ValueError("MOH DLL must be a regular file, not a symlink")
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != PIN:
        raise ValueError("MOH DLL SHA256 does not match the verified original")
    return PeImage(data).parse_tls()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dll", type=Path, help="original private MOH DLL or 7_Fingerprint-module.zip")
    args = parser.parse_args()
    try:
        with tempfile.TemporaryDirectory(prefix="ft5955-moh-tls-") as tmp:
            path = (archive_engine(args.dll, Path(tmp))
                    if args.dll.suffix.lower() == ".zip" else args.dll)
            result = audit_file(path)
    except (ValueError, OSError, zipfile.BadZipFile) as exc:
        print(f"Offline MOH TLS preflight failed: {exc}", file=sys.stderr)
        return 2
    print("Verified 5955 MOH engine — OFFLINE PE32+ TLS preflight")
    print("No DLL code executed; no USB or fingerprint data accessed.")
    if result is None:
        print("No TLS directory found. This does not imply the CRT avoids TLS.")
        return 0
    print(f"TLS directory RVA: 0x{result['tls_rva']:x}")
    print(f"Initialised TLS template bytes: {result['template_bytes']}")
    print(f"Additional zero-fill bytes: {result['zero_fill_bytes']}")
    print(f"TLS index VA: 0x{result['index_va']:x}")
    print(f"TLS callback table VA: 0x{result['callbacks_va']:x}")
    print(f"TLS callback count: {len(result['callbacks'])}")
    for i, address in enumerate(result["callbacks"], 1):
        print(f"  callback #{i}: VA 0x{address:x}")
    print(f"TLS characteristics: 0x{result['characteristics']:x}")
    print("Callback presence alone does not prove direct TEB/PEB access.")
    print("Do NOT execute vendor TLS callbacks or DllMain based on this report.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
