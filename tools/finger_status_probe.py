#!/usr/bin/env python3
"""Experimental FocalTech 2808:5955 single-request finger-status probe.

The request comes from the Windows MOH driver's ff_sc_ReadFingerStatus routine,
not from guesswork or another USB product. --send plus an explicit typed SEND
are REQUIRED for hardware communication. Exactly one command is sent per run.

The returned status byte's meaning is NOT established; no enrolment, image
capture, polling, reset, firmware update or authentication changes are made.
"""

from __future__ import annotations

import argparse
import sys

try:
    import usb.core
    import usb.util
except ImportError:
    print(
        "PyUSB missing. Install using .venv/bin/python -m pip install -r requirements.txt",
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

# From the matching Windows MOH DLL:
# ff_sc_ReadFingerStatus at 0x180007818 loads CL=0x82 and uses
# the two-byte buffer {0x73, 0x01} as the outgoing payload.
# It requests one byte of payload in the response.
STATUS_COMMAND = 0x82
STATUS_ARGUMENT = bytes((0x73, 0x01))
AUDITED_REQUEST = bytes.fromhex("02 00 03 82 73 01 f3")


def build_status_request() -> bytes:
    """Build the audited command (pure function; no device access)."""
    packet = encode_command(STATUS_COMMAND, STATUS_ARGUMENT)
    if packet != AUDITED_REQUEST:
        raise SafetyAbort("Built packet does not match the disassembly-derived request.")
    return packet


def read_status_once(packet: bytes) -> int:
    """Claim only the specific USB reader, send once, then read with timeouts."""
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

        written = device.write(ENDPOINT_OUT, packet, timeout=SEND_TIMEOUT_MS)
        print(f"USB OUT completed: {written}/{len(packet)} bytes.")
        if written != len(packet):
            print("Partial transmission. Stopping without retry.", file=sys.stderr)
            return 4

        raw = receive_reply(device)
        if not raw:
            print("No reply. This request may require device setup.")
            return 5

        print(f"USB IN received: {len(raw)} bytes.")
        print("Raw reply (review before sharing):", raw.hex(" "))

        try:
            response = decode_reply(raw)
        except ProtocolError as error:
            print(f"Reply decoding failed: {error}")
            return 6

        print(f"Verified reply type: 0x{response.reply_type:02x}")
        print(f"Valid XOR checksum; trailing zero: {response.trailing_zero}")
        print(f"Response payload: {response.payload.hex(' ')}")
        if len(response.payload) == 1:
            status = response.payload[0]
            print(f"STATUS BYTE: 0x{status:02x} (decimal {status})")
            print(
                "This value is not yet proven to mean finger present/absent. "
                "Compare labelled readings."
            )
            return 0

        print(
            "Unexpected payload size for ff_sc_ReadFingerStatus: "
            f"{len(response.payload)} byte(s); status meaning unknown."
        )
        return 6
    except SafetyAbort as error:
        print(f"SAFETY STOP: {error}", file=sys.stderr)
        return 3
    except usb.core.USBError as error:
        print(f"USB access error: {error}", file=sys.stderr)
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
        "--send",
        action="store_true",
        help="Send the single candidate status-read command to real hardware",
    )
    parser.add_argument(
        "--label",
        choices=("no-finger", "finger"),
        default="no-finger",
        help="What YOU are doing when the command is sent; not inferred by software",
    )
    args = parser.parse_args()
    packet = build_status_request()
    print("FocalTech 2808:5955 experimental finger-status read")
    print("  Derived from Windows: ff_sc_ReadFingerStatus")
    print("  USB OUT packet:", packet.hex(" "))
    print(f"  Observational label: {args.label}")
    print("  Exactly one command per run. No polling, reset or firmware changes.")

    if not args.send:
        print("DRY RUN ONLY: hardware not accessed.")
        return 0

    print()
    print("WARNING: Though the Windows routine is named ReadFingerStatus,")
    print("the command has not been tested on this hardware. Device response")
    print("and side effects cannot be guaranteed.")
    if args.label == "finger":
        print("Keep your finger resting on the sensor before confirming.")
    else:
        print("Keep your finger OFF the sensor before confirming.")

    try:
        confirmed = input("Type SEND to transmit one USB request: ")
    except (EOFError, KeyboardInterrupt):
        print("\nCancelled without sending.")
        return 3
    if confirmed != "SEND":
        print("Cancelled without sending.")
        return 3

    return read_status_once(packet)


if __name__ == "__main__":
    raise SystemExit(main())
