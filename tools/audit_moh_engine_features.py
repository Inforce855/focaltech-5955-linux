#!/usr/bin/env python3
"""Read-only audit of the exact FocalTech 2808:5955 MOH matching engine.

Requires private vendor DLL supplied by operator. Reads NO biometric data and
prints NO proprietary table contents, fingerprint images, or template bytes.
"""
import argparse
import hashlib
import math
import struct
from collections import Counter
from pathlib import Path

EXPECTED_SHA = "a4f037c260e8c86718675ddb6540467a9006ab26184858eb5b8726137185d57c"
IMAGE_BASE = 0x180000000


def sections(blob):
    if len(blob) < 0x200 or blob[:2] != b"MZ":
        raise ValueError("Not an MZ executable")
    pe = struct.unpack_from("<I", blob, 0x3C)[0]
    if pe + 24 > len(blob) or blob[pe:pe+4] != b"PE\0\0":
        raise ValueError("Not a PE executable")
    count = struct.unpack_from("<H", blob, pe + 6)[0]
    optional = struct.unpack_from("<H", blob, pe + 20)[0]
    if struct.unpack_from("<H", blob, pe + 24)[0] != 0x20B:
        raise ValueError("Expected x64 PE32+ format")
    start = pe + 24 + optional
    if start + count * 40 > len(blob):
        raise ValueError("Truncated PE sections")
    result = []
    for i in range(count):
        pos = start + i * 40
        name = blob[pos:pos+8].split(b"\0")[0].decode("ascii", "replace")
        vs, rva, raw_size, raw_pos = struct.unpack_from("<IIII", blob, pos + 8)
        result.append((name, rva, vs, raw_size, raw_pos))
    return result


def data_at(blob, sect, virtual_address, size):
    rva = virtual_address - IMAGE_BASE
    if size <= 0:
        raise ValueError("Invalid requested size")
    for name, start, vs, raw_size, raw_pos in sect:
        if start <= rva and rva + size <= start + raw_size:
            pos = raw_pos + rva - start
            if pos + size > len(blob):
                raise ValueError("Truncated section")
            return blob[pos:pos + size]
    raise ValueError("Virtual address is not in a backed PE section: " + hex(virtual_address))


def audit(dll):
    blob = Path(dll).read_bytes()
    if hashlib.sha256(blob).hexdigest() != EXPECTED_SHA:
        raise ValueError("Different vendor DLL SHA256; refusing to generalize")
    sect = sections(blob)
    mode = data_at(blob, sect, 0x180225C51, 1)[0]
    intervals, curvature = struct.unpack("<ii", data_at(blob, sect, 0x180225C30, 8))
    sigma, contrast = struct.unpack("<ff", data_at(blob, sect, 0x180225C38, 8))
    point_data = data_at(blob, sect, 0x1801EAE20, 45 * 8)
    points = [struct.unpack_from("<ff", point_data, i * 8) for i in range(45)]
    radii = Counter(round(math.hypot(x, y)) for x, y in points)
    if sorted(radii.items()) != [(4, 10), (8, 15), (13, 20)]:
        raise ValueError("Sample point geometry differs")
    pairs = data_at(blob, sect, 0x1801EAC20, 512)
    if max(pairs) >= 45 or any(pairs[i] == pairs[i+1] for i in range(0, 512, 2)):
        raise ValueError("Invalid point-pair indices")
    checks = {
        "64 loop groups": (0x1800C8C18, bytes.fromhex("45 8d 4a 40")),
        "bit-set opcode": (0x1800C8C5B, bytes.fromhex("44 0f ab c0")),
        "44-byte record step": (0x1800C8D87, bytes.fromhex("48 83 c3 2c")),
        "44-byte record allocation": (0x1800C32C9, bytes.fromhex("6b cb 2c")),
    }
    for label, (address, code) in checks.items():
        if data_at(blob, sect, address, len(code)) != code:
            raise ValueError("Unexpected assembly signature for " + label)
    print("MOH engine feature audit — private DLL checksum verified")
    print("Initial algorithm mode: %d (MFB when unmodified; runtime mode unknown)" % mode)
    print("Initial scale intervals: %d; curvature threshold: %d" % (intervals, curvature))
    print("Initial sigma: %.6g; contrast threshold: %.6g" % (sigma, contrast))
    print("Sample positions: 45, in concentric rings radius 4 x10, 8 x15, 13 x20")
    print("Descriptor: 256 non-self sample pairs; indices within 0..44; all points used")
    print("64 groups x 4 comparisons = 256 bit decisions")
    print("Feature stride: 44 bytes (12 bytes metadata + 32 descriptor bytes)")
    print("Instruction checks: loop, bit setting, stride and allocation matched")
    print("No biometric or proprietary lookup data printed or saved")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("vendor_engine_dll", type=Path, help="Private ftWbioEngineAdapter.dll")
    args = parser.parse_args()
    try:
        audit(args.vendor_engine_dll)
    except (ValueError, OSError, struct.error) as error:
        parser.exit(1, "Audit failed: " + str(error) + "\n")


if __name__ == "__main__":
    main()
