"""Versioned FT5955 MOH driver data format: only private, memory-only use.

Reference implementation for the native C codec. Not encryption, secure
storage or a complete libfprint FpPrint serialisation implementation.
"""
from __future__ import annotations
import hashlib
import hmac
import struct

MAGIC = b'FT5955P1'
HEADER = struct.Struct('<8sBBBBHHI')
MAX_TEMPLATE = 1024 * 1024
OVERHEAD = HEADER.size + 32


def encode(template: bytes | bytearray, subfactor: int) -> bytearray:
    if not 1 <= len(template) <= MAX_TEMPLATE or not 0 <= subfactor <= 255:
        raise ValueError('Invalid MOH template or subfactor')
    header = HEADER.pack(MAGIC, 1, 1, subfactor, 0, 0x2808, 0x5955, len(template))
    data = bytearray(header)
    data.extend(template)
    data.extend(hashlib.sha256(data).digest())
    return data


def decode(envelope: bytes | bytearray) -> tuple[bytearray, int]:
    if not HEADER.size + 1 + 32 <= len(envelope) <= HEADER.size + MAX_TEMPLATE + 32:
        raise ValueError('Invalid print size')
    magic, alg, polarity, subfactor, flags, vid, pid, size = HEADER.unpack_from(envelope)
    if (magic != MAGIC or alg != 1 or polarity != 1 or flags != 0 or
            vid != 0x2808 or pid != 0x5955 or size == 0 or size > MAX_TEMPLATE or
            len(envelope) != HEADER.size + size + 32):
        raise ValueError('Unsupported or corrupt print metadata')
    if not hmac.compare_digest(
            hashlib.sha256(memoryview(envelope)[:-32]).digest(),
            memoryview(envelope)[-32:]):
        raise ValueError('Print integrity check failed')
    return bytearray(memoryview(envelope)[HEADER.size:-32]), subfactor


def wipe(buffer: bytearray) -> None:
    buffer[:] = b'\x00' * len(buffer)
