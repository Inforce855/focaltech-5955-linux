#!/usr/bin/env python3
"""Controlled, single-image FocalTech 2808:5955 preflight experiment.

Exercises ONLY four requests already verified individually on this hardware:
0x34 handshake, 0x82 finger status, 0x80 readiness word and 0x81 image read.
This is NOT the complete Windows initialisation. In particular, the vendor
mode-6 0x87 state change and its unknown idle restoration are NOT attempted.

Dry run by default. --send requires the operator to place a finger and type
CAPTURE. Sends at most one of each packet; any failure stops. No USB reset,
reconfiguration, driver binding, polling, automatic retries, or fprintd/PAM.
A verified image is stored privately in ignored local-data/ only.
"""
from __future__ import annotations

import argparse
import sys
import time

from image_capture_probe import save_private_raw
from image_transfer import RAW_LENGTH, extract_image, receive_limited
from protocol_codec import ProtocolError, decode_reply, encode_command

# These exact packets have been individually checked on the user's 5955.
STEPS = (
    ("Handshake (0x34)", 0x34, b"", bytes.fromhex("02 00 01 34 35")),
    ("Finger status (0x82)", 0x82, b"\x73\x01",
     bytes.fromhex("02 00 03 82 73 01 f3")),
    ("Readiness (0x80)", 0x80, b"\x01\x02",
     bytes.fromhex("02 00 03 80 01 02 80")),
    ("Image (0x81)", 0x81, b"", bytes.fromhex("02 00 01 81 80")),
)


def checked_packets() -> tuple[bytes, ...]:
    """Refuse to send if any byte differs from the previously audited request."""
    packets = []
    for name, cmd, payload, audited in STEPS:
        packet = encode_command(cmd, payload)
        if packet != audited:
            raise ValueError(f"{name}: request differs from audited bytes")
        packets.append(packet)
    return tuple(packets)


def decode_preflight_reply(raw: bytes, stage: str) -> int:
    """Validate small response frame and expected marker; no image data."""
    reply = decode_reply(raw)
    if reply.prefix != 0x02 or len(reply.payload) != (1 if stage == "finger" else 2):
        raise ProtocolError(f"{stage}: unexpected response prefix or payload length")
    if stage == "handshake":
        word = int.from_bytes(reply.payload, "little")
        if word != 0xAA55:
            raise ProtocolError(f"Handshake marker 0x{word:04x}, expected 0xaa55")
        return word
    if stage == "ready":
        word = int.from_bytes(reply.payload, "little")
        if word != 0x5AA5:
            raise ProtocolError(f"Readiness marker 0x{word:04x}, expected 0x5aa5")
        return word
    if stage == "finger":
        status = reply.payload[0]
        if status not in (0x05, 0x06):
            raise ProtocolError(f"Unexpected contact status 0x{status:02x}")
        return status
    raise ValueError("Unexpected stage name")


def count_blank_rows(raw: bytes) -> tuple[int, int, int, float]:
    """Aggregate only: leading full-zero rows, total, bottom, percent zeros.

    Works on the stored 64x80 interpretation of 5120 LE 16-bit samples,
    without deriving, printing or publishing biometric image detail.
    """
    if len(raw) != RAW_LENGTH:
        raise ValueError("Expected 10240 raw bytes")
    words = [int.from_bytes(raw[i:i + 2], "little")
             for i in range(0, RAW_LENGTH, 2)]
    zero_by_row = [sum(v == 0 for v in words[y * 64:(y + 1) * 64])
                   for y in range(80)]
    leading = 0
    for n in zero_by_row:
        if n != 64:
            break
        leading += 1
    trailing = 0
    for n in reversed(zero_by_row):
        if n != 64:
            break
        trailing += 1
    return (leading, sum(n == 64 for n in zero_by_row), trailing,
            100.0 * sum(zero_by_row) / 5120.0)


def run_live(packets: tuple[bytes, ...]) -> int:
    try:
        import usb.core
        import usb.util
        from firmware_probe import (
            ENDPOINT_IN, ENDPOINT_OUT, INTERFACE, PID, SEND_TIMEOUT_MS,
            SafetyAbort, VID, receive_reply, timed_out, validate_device,
        )
    except ImportError:
        print("PyUSB missing from project Python environment.", file=sys.stderr)
        return 2

    device = usb.core.find(idVendor=VID, idProduct=PID)
    if device is None:
        print("Exact reader 2808:5955 not found.", file=sys.stderr)
        return 1

    claimed = False
    try:
        validate_device(device)
        usb.util.claim_interface(device, INTERFACE)
        claimed = True

        def exchange(index: int, *, image: bool = False) -> bytes:
            name = STEPS[index][0]
            started = time.perf_counter()
            sent = device.write(ENDPOINT_OUT, packets[index],
                                timeout=SEND_TIMEOUT_MS)
            if sent != len(packets[index]):
                raise ProtocolError(f"{name}: partial USB write; no retry")
            if image:
                data = receive_limited(
                    lambda count, timeout: device.read(
                        ENDPOINT_IN, count, timeout=timeout),
                    seconds=15.0)
            else:
                data = receive_reply(device)
            print(f"  {name}: {len(data)} reply bytes; "
                  f"{1000 * (time.perf_counter()-started):.1f} ms")
            if not data:
                raise ProtocolError(f"{name}: no response; stopping")
            return data

        handshake = decode_preflight_reply(exchange(0), "handshake")
        print(f"  Handshake: 0x{handshake:04x} (expected)")
        contact = decode_preflight_reply(exchange(1), "finger")
        print(f"  Finger contact: 0x{contact:02x} "
              f"({'present' if contact == 5 else 'absent'})")
        if contact != 0x05:
            print("STOP: No finger detected. Image request not sent.")
            return 5

        # The Windows driver waits after setting scan mode. We do NOT set it;
        # this short pause does not make its idle readiness marker reliable.
        time.sleep(0.010)
        ready = decode_preflight_reply(exchange(2), "ready")
        print(f"  Readiness word: 0x{ready:04x} "
              "(marker also appears when scan mode is NOT enabled)")
        frame = exchange(3, image=True)
        image = extract_image(frame)
        leading, total, trailing, zero_pct = count_blank_rows(image.pixels)
        print(f"  Image transport: {image.format}")
        print(f"  Raw zeros: {zero_pct:.1f}% | "
              f"leading blank rows: {leading} | "
              f"all-blank rows: {total} | "
              f"trailing blank rows: {trailing} (64x80)")
        if total or zero_pct >= 15.0:
            print("  IMAGE QUALITY WARNING: missing regions; "
                  "do not use this capture as an enrollment reference.")
        saved = save_private_raw(image.pixels)
        print(f"  Saved privately: {saved}")
        print("  Keep biometric data local. Share only the text results.")
        return 0
    except SafetyAbort as exc:
        print(f"SAFETY STOP: {exc}", file=sys.stderr)
        return 3
    except ProtocolError as exc:
        print(f"STOP: {exc}", file=sys.stderr)
        return 6
    except usb.core.USBError as exc:
        print("USB error; no retries or mode changes.", file=sys.stderr)
        if timed_out(exc):
            print("USB read timed out.", file=sys.stderr)
        return 4
    except (OSError, ValueError) as exc:
        print(f"STOP: {exc}", file=sys.stderr)
        return 7
    except KeyboardInterrupt:
        print("\nInterrupted; no further requests.", file=sys.stderr)
        return 130
    finally:
        if claimed:
            try:
                usb.util.release_interface(device, INTERFACE)
            except usb.core.USBError:
                print("Warning: unable to release interface.", file=sys.stderr)
        usb.util.dispose_resources(device)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--send", action="store_true",
                        help="perform one opt-in preflight plus one image read")
    args = parser.parse_args()
    try:
        packets = checked_packets()
    except ValueError as exc:
        print(f"SAFETY STOP: {exc}", file=sys.stderr)
        return 3

    print("FocalTech 5955 — existing-command acquisition preflight")
    print("Sequence: handshake -> contact -> readiness -> ONE image request")
    print("NO 0x87 mode changes, reset, polling, driver or USB power changes.")
    for step, packet in zip(STEPS, packets):
        print(f"  {step[0]}: {packet.hex(' ')}")
    if not args.send:
        print("DRY RUN: no USB request sent; no files created.")
        return 0

    print("Place a finger gently on the sensor BEFORE confirming.")
    print("This sends up to FOUR previously tested USB requests, in sequence.")
    print("It is NOT the full Windows scan-mode initialisation.")
    try:
        confirmation = input("Type CAPTURE to proceed (anything else cancels): ")
    except (KeyboardInterrupt, EOFError):
        print("\nCancelled; no USB requests sent.")
        return 3
    if confirmation != "CAPTURE":
        print("Cancelled; no USB requests sent.")
        return 3
    return run_live(packets)


if __name__ == "__main__":
    raise SystemExit(main())
