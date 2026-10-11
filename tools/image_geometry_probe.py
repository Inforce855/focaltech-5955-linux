#!/usr/bin/env python3
"""Read one sensor image dimension from FocalTech 2808:5955, if explicitly allowed.

The Windows MOH DLL's image setup routine requests sensor geometry using
logical command 0x80. This tool issues ONLY one 1-byte metadata read:
  height: 0x80 with payload 03 01
  width:  0x80 with payload 04 01

The field selection is reconstructed from the DLL, but the values and behaviour
are still unverified on the live sensor.

No scan, image capture, firmware update, reset, enrolment or persistent writes.
Default mode is entirely offline. --send requires typing SEND.
"""

from __future__ import annotations

import argparse
import sys

try:
    import usb.core
    import usb.util
except ImportError:
    print(
        "PyUSB missing. Install: .venv/bin/python -m pip install -r requirements.txt",
        file=sys.stderr,
    )
    raise SystemExit(2)

from firmware_probe import (
    BCD_DEVICE,
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

# In FtWbioDriverUmdfV3.dll, function 0x180008328:
# - first invokes 0x180007b8c with selector 03 and one-byte response written
#   into the device structure's +0x5b field (height candidate);
# - next invokes 0x180007b8c with selector 04 and response written into
#   +0x5a (width candidate);
# - then multiplies those fields, storing +0x5c pixel count.
# Function 0x180007b8c sends command 80 with (selector, 01) payload.
GEOMETRY_FIELDS = {
    "height": (bytes.fromhex("03 01"), bytes.fromhex("02 00 03 80 03 01 81")),
    "width": (bytes.fromhex("04 01"), bytes.fromhex("02 00 03 80 04 01 86")),
}


def packet_for_field(field: str) -> bytes:
    """Pure offline packet builder: never touches the device."""
    payload, known_packet = GEOMETRY_FIELDS[field]
    packet = encode_command(0x80, payload)
    if packet != known_packet:
        raise SafetyAbort("Constructed packet differs from the analysed bytes.")
    return packet


def query_dimension_once(field: str, packet: bytes) -> int:
    device = usb.core.find(idVendor=VID, idProduct=PID)
    if device is None:
        print("FocalTech 2808:5955 not found.", file=sys.stderr)
        return 1

    claimed = False
    try:
        validate_device(device)
        print(f"Matched FocalTech {VID:04x}:{PID:04x}, bcdDevice {BCD_DEVICE:04x}.")
        usb.util.claim_interface(device, INTERFACE)
        claimed = True

        # Exactly one bulk OUT request, without retries or extra commands.
        written = device.write(ENDPOINT_OUT, packet, timeout=SEND_TIMEOUT_MS)
        print(f"USB OUT: {written}/{len(packet)} bytes.")
        if written != len(packet):
            print("Partial write, stopping without a retry.", file=sys.stderr)
            return 4

        reply = receive_reply(device)
        if not reply:
            print("No reply; no further requests will be sent.")
            return 5

        print(f"USB IN: {len(reply)} bytes.")
        print("Response frame:", reply.hex(" "))
        try:
            parsed = decode_reply(reply)
        except ProtocolError as error:
            print(f"Invalid response framing/checksum: {error}")
            return 6

        if len(parsed.payload) != 1:
            print(
                "Unexpected response payload size:",
                len(parsed.payload), "byte(s).",
            )
            return 6

        value = parsed.payload[0]
        print(f"Reported {field.upper()}: {value} pixel(s) (0x{value:02x}).")
        print("Result is a reported metadata value, not an image capture.")
        if value == 0:
            print("Zero is not a usable image dimension; inspect the setup sequence.")
            return 6
        return 0
    except SafetyAbort as error:
        print(f"SAFETY STOP: {error}", file=sys.stderr)
        return 3
    except usb.core.USBError as error:
        print(f"USB error: {error}", file=sys.stderr)
        return 4
    except KeyboardInterrupt:
        print("\nInterrupted. No command retries.")
        return 130
    finally:
        if claimed:
            try:
                usb.util.release_interface(device, INTERFACE)
            except usb.core.USBError as error:
                print(f"Warning: interface release failed: {error}", file=sys.stderr)
        usb.util.dispose_resources(device)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dimension",
        choices=("height", "width"),
        default="height",
        help="single metadata value to request (default height)",
    )
    parser.add_argument(
        "--send",
        action="store_true",
        help="opt in to exactly one real USB metadata request",
    )
    args = parser.parse_args()

    packet = packet_for_field(args.dimension)
    print("FocalTech 2808:5955 — experimental image geometry probe")
    print(f"Dimension: {args.dimension}")
    print("USB OUT:", packet.hex(" "))
    print("No image scan, capture, enrolment or configuration changes.")
    if not args.send:
        print("DRY RUN: no USB access.")
        return 0

    print("WARNING: this candidate is reconstructed from the MOH Windows")
    print("DLL but has not been verified on this sensor. Effects cannot be")
    print("guaranteed until tested; type SEND only if you accept this risk.")
    try:
        answer = input("Type SEND to transmit one request: ")
    except (EOFError, KeyboardInterrupt):
        print("\nCancelled without sending.")
        return 3
    if answer != "SEND":
        print("Cancelled without sending.")
        return 3

    return query_dimension_once(args.dimension, packet)


if __name__ == "__main__":
    raise SystemExit(main())
