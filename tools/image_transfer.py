"""Offline parser for a candidate FocalTech 80x64 raw-image transfer.

No USB I/O, image logging or biometric files. The large-image wire
format has NOT yet been validated on the physical fingerprint reader.
"""
from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Callable

from protocol_codec import ProtocolError, decode_reply

WIDTH = 80
HEIGHT = 64
RAW_LENGTH = WIDTH * HEIGHT * 2  # 10240
FRAMED_LENGTH = RAW_LENGTH + 5   # prefix + BE length + type + checksum
MAX_WIRE_BYTES = FRAMED_LENGTH + 1  # optional single trailer; image trailer unverified


@dataclass(frozen=True)
class TransferImage:
    pixels: bytes
    format: str


def is_complete_transfer(data: bytes) -> bool:
    """Detect an expected full raw payload, image frame or short status."""
    if len(data) > MAX_WIRE_BYTES:
        return True
    if len(data) >= 3 and data[0] == 0x02:
        declared = int.from_bytes(data[1:3], 'big')
        if 1 <= declared <= RAW_LENGTH + 1:
            wire_size = declared + 4
            if len(data) >= wire_size:
                return True
            if declared == RAW_LENGTH + 1:
                return False
    return len(data) >= RAW_LENGTH


def extract_image(data: bytes) -> TransferImage:
    """Accept only an exact raw buffer or a valid checksummed image frame.

    Prevent partial framed images being mistaken for unframed data.
    No file is written unless the caller receives an accepted image.
    """
    if len(data) > MAX_WIRE_BYTES:
        raise ProtocolError('Transfer exceeds the 80x64 image safety limit')
    if len(data) >= 3 and data[0] == 0x02:
        declared = int.from_bytes(data[1:3], 'big')
        if declared == RAW_LENGTH + 1:
            # The hardware returned 10246 bytes on the first 0x81 test.
            # Short replies used a 00 trailer, but the last byte of that
            # image-sized reply was not 00. Rather than assuming the trailer
            # is part of the image or ignoring a bad checksum, validate the
            # FIRST 10245 bytes as a complete independent protocol frame.
            # Only then is a *single* unverified transport trailer ignored.
            if len(data) not in (FRAMED_LENGTH, FRAMED_LENGTH + 1):
                raise ProtocolError(
                    f'Image frame needs {FRAMED_LENGTH} bytes plus at most '
                    f'one trailer; got {len(data)} bytes'
                )
            trailer = data[FRAMED_LENGTH] if len(data) == FRAMED_LENGTH + 1 else None
            reply = decode_reply(data[:FRAMED_LENGTH])
            if reply.prefix != 0x02 or len(reply.payload) != RAW_LENGTH:
                raise ProtocolError('Framed image dimensions/type differ from expected')
            if trailer is None:
                description = 'framed/checksummed, no trailer'
            elif trailer == 0:
                description = 'framed/checksummed, trailing 00'
            else:
                description = 'framed/checksummed, nonzero trailer (meaning UNVERIFIED)'
            return TransferImage(reply.payload, description)
        if declared + 4 == len(data) or declared + 5 == len(data):
            raise ProtocolError('Sensor returned a non-image response, not pixel data')
    if len(data) == RAW_LENGTH:
        return TransferImage(data, 'unframed/UNVERIFIED')
    raise ProtocolError(f'Incomplete/unrecognised image transfer ({len(data)} bytes)')


def receive_limited(read_chunk: Callable[[int, int], bytes],
                    *, seconds: float = 15.0) -> bytes:
    """Collect one bulk IN stream with maximum length/time/fragment limits.

    The caller supplies read_chunk(max_size, timeout_ms). This never retries
    an OUT request, never sends USB commands and never prints pixel contents.
    """
    out = bytearray()
    deadline = time.monotonic() + seconds
    for _ in range(192):
        if time.monotonic() >= deadline:
            break
        remaining = MAX_WIRE_BYTES - len(out)
        if remaining <= 0 or is_complete_transfer(out):
            break
        timeout = min(2500 if not out else 500,
                      max(100, int((deadline - time.monotonic()) * 1000)))
        part = bytes(read_chunk(min(64, remaining), timeout))
        if not part:
            break
        if len(part) > min(64, remaining):
            raise ProtocolError('Oversized USB fragment')
        out.extend(part)
        if is_complete_transfer(out):
            break
    return bytes(out)
