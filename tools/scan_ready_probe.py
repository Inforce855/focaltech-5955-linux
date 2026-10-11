#!/usr/bin/env python3
"""One-shot, experimental FocalTech 2808:5955 scan-readiness register read.

Derived from the Windows MOH DLL's routine at image VA 0x180009B94.
Reads selector 0x01, requesting a two-byte value (0x80 request).
Windows compares the little-endian result to 0x5AA5.

This is NOT a scan request or an image capture. The hardware command has not
been verified on this sensor yet. It may return a non-ready result because we
have not activated scan mode, and its effects cannot be guaranteed.

Default invocation is offline. A single real USB OUT requires both --send
and manually entering SEND; there are no write retries or mode changes.
"""

from __future__ import annotations

import argparse
import sys

try:
    import usb.core
    import usb.util
except ImportError:
    print("PyUSB is required. Install the project requirements first.", file=sys.stderr)
    raise SystemExit(2)

from firmware_probe import (
    ENDPOINT_OUT,
    INTERFACE,
    PID,
    SEND_TIMEOUT_MS,
    SafetyAbort,
    VID,
    receive_reply,
    validate_device,
)
from protocol_codec import ProtocolError, decode_reply, encode_command

READY_REGISTER = 0x01
REQUESTED_LENGTH = 0x02
LOGICAL_COMMAND = 0x80
AUDITED_PACKET = bytes.fromhex("02 00 03 80 01 02 80")
EXPECTED_READY_WORD = 0x5AA5


def build_request() -> bytes:
    """Construct the disassembly-derived request; no hardware access."""
    packet = encode_command(
        LOGICAL_COMMAND,
        bytes((READY_REGISTER, REQUESTED_LENGTH)),
    )
    if packet != AUDITED_PACKET:
        raise SafetyAbort("Encoded request differs from the audited bytes.")
    return packet


def query_once(packet: bytes) -> int:
    """Send at most one metadata query to the exact expected USB device."""
    device = usb.core.find(idVendor=VID, idProduct=PID)
    if device is None:
        print("FocalTech 2808:5955 not found.", file=sys.stderr)
        return 1

    claimed = False
    try:
        validate_device(device)
        usb.util.claim_interface(device, INTERFACE)
        claimed = True

        written = device.write(ENDPOINT_OUT, packet, timeout=SEND_TIMEOUT_MS)
        print(f"USB OUT: {written}/{len(packet)} bytes.")
        if written != len(packet):
            print("Partial request; no retry will be attempted.", file=sys.stderr)
            return 4

        frame = receive_reply(device)
        if not frame:
            print("No reply. Scan mode is not being enabled by this application.")
            return 5

        print(f"USB IN: {len(frame)} bytes.")
        print("Raw response:", frame.hex(" "))
        try:
            parsed = decode_reply(frame)
        except ProtocolError as exc:
            print(f"Response failed frame validation: {exc}", file=sys.stderr)
            return 6

        print(f"Reply type: 0x{parsed.reply_type:02x}.")
        print(f"Checksum: valid. One extra trailing zero: {parsed.trailing_zero}.")
        if len(parsed.payload) != 2:
            print(f"Expected two status bytes, got {len(parsed.payload)}.", file=sys.stderr)
            return 6

        value = int.from_bytes(parsed.payload, "little")
        print("Status bytes:", parsed.payload.hex(" "))
        print(f"Readiness word (little-endian): 0x{value:04x}")
        if value == EXPECTED_READY_WORD:
            print("Matches Windows' expected READY marker (0x5AA5).")
        else:
            print("Different from Windows' READY marker (0x5AA5).")
            print("This may be normal before activating scan mode.")
        print("No scan mode change or fingerprint capture was requested.")
        return 0
    except SafetyAbort as exc:
        print(f"SAFETY STOP: {exc}", file=sys.stderr)
        return 3
    except usb.core.USBError as exc:
        print(f"USB error: {exc}", file=sys.stderr)
        return 4
    except KeyboardInterrupt:
        print("\nInterrupted; no retries.")
        return 130
    finally:
        if claimed:
            try:
                usb.util.release_interface(device, INTERFACE)
            except usb.core.USBError as exc:
                print(f"Warning: interface release failed: {exc}", file=sys.stderr)
        usb.util.dispose_resources(device)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--send", action="store_true",
        help="send exactly one live readiness query after confirmation",
    )
    args = parser.parse_args()
    try:
        request = build_request()
    except SafetyAbort as exc:
        print(f"SAFETY STOP: {exc}", file=sys.stderr)
        return 3

    print("FocalTech 2808:5955 candidate readiness-state query")
    print("OUT bytes:", request.hex(" "))
    print("Expected Windows ready marker: 0x5AA5 (two bytes, little-endian).")
    print("Does not enable scanning or acquire an image.")
    if not args.send:
        print("DRY RUN: no USB access.")
        return 0

    print()
    print("CAUTION: This reconstructed request has not been verified on this")
    print("hardware. Its effect cannot be guaranteed, even though it appears")
    print("to read a status value in the matching Windows DLL.")
    try:
        confirmation = input("Type SEND to transmit one USB request: ")
    except (EOFError, KeyboardInterrupt):
        print("\nCancelled without sending.")
        return 3
    if confirmation != "SEND":
        print("Cancelled without sending.")
        return 3
    return query_once(request)


if __name__ == "__main__":
    raise SystemExit(main())
