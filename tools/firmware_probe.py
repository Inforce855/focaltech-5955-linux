#!/usr/bin/env python3
"""Experimental single-shot FocalTech 2808:5955 firmware-info USB query.

Without --send this is an entirely offline dry run. With --send and explicit
terminal confirmation, it sends ONE statically reconstructed firmware-info
request to the specifically checked sensor, then reads at most two responses.
It never sends initialisation, reset, enrolment or firmware-update commands.

WARNING: Until verified against hardware, the effect of any guessed or
reverse-engineered command is not guaranteed.
"""

from __future__ import annotations

import argparse
import errno
import sys

try:
    import usb.core
    import usb.util
except ImportError:
    print(
        "PyUSB is required. Install: .venv/bin/python -m pip install -r requirements.txt",
        file=sys.stderr,
    )
    raise SystemExit(2)

from protocol_codec import ProtocolError, decode_reply, encode_command

VID = 0x2808
PID = 0x5955
BCD_DEVICE = 0x2003
CONFIGURATION = 1
INTERFACE = 0
ENDPOINT_OUT = 0x01
ENDPOINT_IN = 0x82
PACKET_SIZE = 64
FIRMWARE_INFORMATION_COMMAND = 0x30
MAX_REPLY_BYTES = 68  # Firmware-info caller requests up to 63 payload bytes.
SEND_TIMEOUT_MS = 1000
FIRST_READ_TIMEOUT_MS = 2000
SECOND_READ_TIMEOUT_MS = 800


class SafetyAbort(Exception):
    """Refusal to communicate because hardware/conditions do not match."""


def validate_device(device: usb.core.Device) -> None:
    """Reject anything other than the exact observed USB reader configuration."""
    if (device.idVendor, device.idProduct) != (VID, PID):
        raise SafetyAbort("Unexpected USB vendor/product ID.")
    if device.bcdDevice != BCD_DEVICE:
        raise SafetyAbort(
            f"Device revision {device.bcdDevice:04x} differs from tested 2003."
        )
    configurations = list(device)
    if len(configurations) != 1:
        raise SafetyAbort("Unexpected number of USB configurations.")
    config = device.get_active_configuration()
    if config.bConfigurationValue != CONFIGURATION:
        raise SafetyAbort("Configuration 1 is not already active; refusing to change it.")

    try:
        interface = config[(INTERFACE, 0)]
    except IndexError as error:
        raise SafetyAbort("Expected interface 0, alternate 0 was not found.") from error

    if (interface.bInterfaceClass, interface.bInterfaceSubClass,
            interface.bInterfaceProtocol) != (0x0A, 0, 0):
        raise SafetyAbort("USB interface class/subclass/protocol is unexpected.")

    expected = {ENDPOINT_OUT, ENDPOINT_IN}
    seen = set()
    for endpoint in interface:
        if usb.util.endpoint_type(endpoint.bmAttributes) != usb.util.ENDPOINT_TYPE_BULK:
            raise SafetyAbort("Non-bulk endpoint present; refusing to send.")
        if endpoint.wMaxPacketSize != PACKET_SIZE:
            raise SafetyAbort("Unexpected USB endpoint packet size.")
        seen.add(endpoint.bEndpointAddress)
    if seen != expected:
        raise SafetyAbort(f"Expected endpoints 01 and 82, found {sorted(seen)!r}.")

    # Crucially, never detach or replace an existing kernel driver.
    try:
        if device.is_kernel_driver_active(INTERFACE):
            raise SafetyAbort("A kernel driver owns interface 0; refusing to detach it.")
    except NotImplementedError as error:
        raise SafetyAbort("Could not confirm kernel-driver ownership.") from error
    except usb.core.USBError as error:
        raise SafetyAbort(f"Could not check kernel-driver ownership: {error}") from error


def timed_out(error: usb.core.USBError) -> bool:
    return (getattr(error, "errno", None) == errno.ETIMEDOUT
            or getattr(error, "backend_error_code", None) == -7)


def receive_reply(device: usb.core.Device) -> bytes:
    """Receive at most two bulk IN transfers, with bounded waiting."""
    received = bytearray()
    for timeout in (FIRST_READ_TIMEOUT_MS, SECOND_READ_TIMEOUT_MS):
        try:
            chunk = bytes(device.read(ENDPOINT_IN, 128, timeout=timeout))
        except usb.core.USBError as error:
            if timed_out(error):
                if not received:
                    print("USB IN timed out. No response to the single command.")
                else:
                    print("USB IN timed out after a partial response.")
                return bytes(received)
            raise

        if not chunk:
            return bytes(received)
        received.extend(chunk)

        if len(received) >= 3:
            expected_size = int.from_bytes(received[1:3], "big") + 4
            if not 5 <= expected_size <= MAX_REPLY_BYTES:
                print("Unexpected response length header; stopping additional reads.")
                break
            if len(received) >= expected_size:
                break
        if len(received) > MAX_REPLY_BYTES:
            print("Unexpectedly large response; stopping additional reads.")
            break
    return bytes(received)


def run_live(packet: bytes) -> int:
    device = usb.core.find(idVendor=VID, idProduct=PID)
    if device is None:
        print("Sensor 2808:5955 is not present.", file=sys.stderr)
        return 1

    claimed = False
    try:
        validate_device(device)
        print(f"Matched sensor: {VID:04x}:{PID:04x}, USB revision 20.03.")
        print("USB configuration and endpoints match the earlier Nobara observations.")
        usb.util.claim_interface(device, INTERFACE)
        claimed = True

        # This is the ONLY bulk OUT transfer anywhere in this programme.
        written = device.write(ENDPOINT_OUT, packet, timeout=SEND_TIMEOUT_MS)
        print(f"USB OUT completed: {written} of {len(packet)} bytes.")
        if written != len(packet):
            print("Partial write; stopping without retry.", file=sys.stderr)
            return 4

        reply = receive_reply(device)
        if not reply:
            print("RESULT: No sensor response. It may require initialisation.")
            return 5

        print(f"USB IN received {len(reply)} bytes.")
        print("Raw reply (review before sharing; could contain identifying data):")
        print(" ", reply.hex(" "))
        try:
            decoded = decode_reply(reply)
        except ProtocolError as error:
            print(f"RESULT: Real USB data arrived, but decoding failed: {error}")
            return 6
        print(f"Reply type: 0x{decoded.reply_type:02x}")
        print("Reply payload (printable text):",
              "".join(chr(c) if 32 <= c <= 126 else "." for c in decoded.payload))
        print("RESULT: Real hardware replied with a valid framed packet.")
        return 0
    except SafetyAbort as error:
        print(f"SAFETY STOP: {error}", file=sys.stderr)
        return 3
    except usb.core.USBError as error:
        print(f"USB error: {error}", file=sys.stderr)
        return 4
    except KeyboardInterrupt:
        print("\nInterrupted. No further command will be sent.")
        return 130
    finally:
        if claimed:
            try:
                usb.util.release_interface(device, INTERFACE)
            except usb.core.USBError as error:
                print(f"Warning: could not release USB interface: {error}",
                      file=sys.stderr)
        usb.util.dispose_resources(device)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--send", action="store_true",
        help="enable one real bulk OUT request; requires interactive confirmation"
    )
    args = parser.parse_args()

    packet = encode_command(FIRMWARE_INFORMATION_COMMAND)
    expected = bytes.fromhex("02 00 01 30 31")
    if packet != expected:
        print("Safety check failed: encoded request differs from audited bytes.",
              file=sys.stderr)
        return 3

    print("FocalTech 2808:5955 firmware-information experiment")
    print(f"  Candidate USB OUT packet: {packet.hex(' ')}")
    print("  Target: endpoint 0x01; response: endpoint 0x82")
    print("  One command only. No retries, reset, enrolment or firmware flashing.")

    if not args.send:
        print("DRY RUN ONLY: nothing was sent to the sensor.")
        print("For one real attempt: sudo .venv/bin/python tools/firmware_probe.py --send")
        return 0

    print()
    print("CAUTION: This command comes from Windows DLL analysis, not a prior")
    print("working hardware trace. Its effect on this sensor is not guaranteed.")
    print("The reader may time out or require initialisation.")
    try:
        confirmation = input("Type SEND to issue this one USB command: ")
    except (EOFError, KeyboardInterrupt):
        print("\nCancelled without sending.")
        return 3
    if confirmation != "SEND":
        print("Cancelled without sending.")
        return 3
    return run_live(packet)


if __name__ == "__main__":
    raise SystemExit(main())
