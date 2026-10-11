#!/usr/bin/env python3
"""Offline FocalTech 2808:5955 MOH USB frame codec from Windows DLL disassembly.

No USB access or hardware control. All packet assumptions are untested on the sensor.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass


class ProtocolError(ValueError):
    """Malformed frame."""


def xor_bcc(data: bytes) -> int:
    """XOR input bytes, initial value zero."""
    value = 0
    for octet in data:
        value ^= octet
    return value


def encode_command(command: int, payload: bytes = b"") -> bytes:
    """Encode: 02 | 2-byte BE length (1+payload) | command | payload | XOR BCC."""
    if not 0 <= command <= 0xFF:
        raise ValueError("Command must be in range 0..255")
    if len(payload) > 0xFFFE:
        raise ValueError("Payload too large")
    body = (len(payload) + 1).to_bytes(2, "big") + bytes([command]) + payload
    return b"\x02" + body + bytes([xor_bcc(body)])


@dataclass(frozen=True)
class Reply:
    prefix: int
    reply_type: int
    payload: bytes


def decode_reply(frame: bytes, *, validate_type: bool = True) -> Reply:
    """Parse a whole candidate response (read from an existing capture).

    The Windows parser checks length, response type 04 and XOR BCC.
    The first byte's required value is still unconfirmed.
    """
    if len(frame) < 5:
        raise ProtocolError("Frame is shorter than five bytes")
    declared_length = int.from_bytes(frame[1:3], "big")
    if declared_length < 1:
        raise ProtocolError("Reply length is zero")
    expected_size = declared_length + 4
    if len(frame) != expected_size:
        raise ProtocolError(
            f"Reply length implies {expected_size} bytes but got {len(frame)}"
        )
    if validate_type and frame[3] != 0x04:
        raise ProtocolError(
            f"Unexpected reply type 0x{frame[3]:02x}; expected 0x04"
        )
    actual_bcc = xor_bcc(frame[1:-1])
    if frame[-1] != actual_bcc:
        raise ProtocolError(
            f"Checksum mismatch: got 0x{frame[-1]:02x}, "
            f"calculated 0x{actual_bcc:02x}"
        )
    return Reply(frame[0], frame[3], frame[4:-1])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--decode", metavar="HEX",
        help="Parse a previously captured reply in hex, entirely offline"
    )
    args = parser.parse_args()
    if args.decode is None:
        print("Firmware-info request (OFFLINE; NOT SENT):")
        print(" ", encode_command(0x30).hex(" "))
        print("This program has no USB/device access.")
        return 0
    try:
        reply = decode_reply(bytes.fromhex(args.decode))
    except ValueError as exc:
        parser.error(str(exc))
    print(f"Prefix: 0x{reply.prefix:02x} (meaning not established)")
    print(f"Reply type: 0x{reply.reply_type:02x}")
    print(f"Data (hex): {reply.payload.hex(' ')}")
    print(
        "Possible ASCII:",
        "".join(chr(b) if 32 <= b < 127 else "." for b in reply.payload)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
