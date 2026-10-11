#!/usr/bin/env python3
"""Single-shot FocalTech 2808:5955 scan-handshake diagnostic.

Derived from the matching Windows MOH driver's routine at VA 0x180009D80.
Sends logical command 0x34 (no payload) and expects a two-byte response.
The Windows caller compares the returned little-endian word to 0xAA55.

The command has NOT yet been verified on this physical reader.
No image, firmware update, reset, enrolment, or scan-mode command is sent.
Default is an offline preview. --send requires explicit SEND confirmation.
"""
from __future__ import annotations

import argparse
import sys

try:
    import usb.core
    import usb.util
except ImportError:
    print("PyUSB required. Install requirements in the project venv.", file=sys.stderr)
    raise SystemExit(2)

from firmware_probe import (
    ENDPOINT_IN, ENDPOINT_OUT, INTERFACE, PID, SEND_TIMEOUT_MS,
    SafetyAbort, VID, receive_reply, validate_device,
)
from protocol_codec import ProtocolError, decode_reply, encode_command

COMMAND = 0x34
EXPECTED_OUT = bytes.fromhex("02 00 01 34 35")


def query_once(packet: bytes) -> int:
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
        print(f"USB OUT: {written}/{len(packet)} bytes")
        if written != len(packet):
            print("Short USB write. No retry.", file=sys.stderr)
            return 4

        raw = receive_reply(device)
        if not raw:
            print("No reply from the sensor; stopping.")
            return 5
        print(f"USB IN: {len(raw)} bytes")
        print("Raw reply:", raw.hex(" "))
        try:
            reply = decode_reply(raw)
        except ProtocolError as err:
            print(f"Response framing/checksum failed: {err}")
            return 6

        if len(reply.payload) != 2:
            print(f"Unexpected data length: {len(reply.payload)} (expected 2)")
            return 6

        status = int.from_bytes(reply.payload, "little")
        print(f"Handshake payload: {reply.payload.hex(' ')}")
        print(f"Little-endian 16-bit value: 0x{status:04x}")
        if status == 0xAA55:
            print("MATCH: Windows driver's expected marker 0xAA55.")
        else:
            print("NO MATCH: Not the marker expected by this Windows routine.")
        print("This is a diagnostic only, not a fingerprint image capture.")
        return 0
    except SafetyAbort as err:
        print(f"Safety stop: {err}", file=sys.stderr)
        return 3
    except usb.core.USBError as err:
        print(f"USB access error: {err}", file=sys.stderr)
        return 4
    except KeyboardInterrupt:
        print("\nInterrupted, no retries.")
        return 130
    finally:
        if claimed:
            try:
                usb.util.release_interface(device, INTERFACE)
            except usb.core.USBError:
                print("Warning: USB interface could not be released.", file=sys.stderr)
        usb.util.dispose_resources(device)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--send", action="store_true",
                        help="send one reconstructed Windows handshake query")
    args = parser.parse_args()
    packet = encode_command(COMMAND)
    if packet != EXPECTED_OUT:
        print("Safety stop: packet does not match audited bytes.", file=sys.stderr)
        return 3

    print("FocalTech 2808:5955 scan-handshake query (candidate)")
    print("USB OUT packet:", packet.hex(" "))
    print("Only one request, no scan-mode setting, no image data.")
    if not args.send:
        print("DRY RUN: hardware not accessed.")
        return 0

    print("This command comes from static DLL analysis and has not yet been")
    print("verified on this exact sensor. Side effects cannot be guaranteed.")
    try:
        confirmed = input("Type SEND to transmit one request: ")
    except (KeyboardInterrupt, EOFError):
        print("\nCancelled.")
        return 3
    if confirmed != "SEND":
        print("Cancelled.")
        return 3
    return query_once(packet)


if __name__ == "__main__":
    raise SystemExit(main())
