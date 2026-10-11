#!/usr/bin/env python3
"""FocalTech 2808:5955 descriptor inspection and opt-in bulk IN listener.

No bulk OUT, vendor-specific control transfers, firmware operations, enrolment
or authentication changes are implemented.
"""

from __future__ import annotations

import argparse
import errno
import sys
import time
from datetime import datetime

try:
    import usb.core
    import usb.util
except ImportError:
    print("PyUSB missing. Install with: .venv/bin/python -m pip install -r requirements.txt",
          file=sys.stderr)
    raise SystemExit(2)

VID = 0x2808
PID = 0x5955
INTERFACE = 0
ENDPOINT_IN = 0x82
ENDPOINT_OUT = 0x01
READ_SIZE = 64
READ_TIMEOUT_MS = 250


def timestamp() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def describe_device(device: usb.core.Device) -> bool:
    """Display cached USB descriptors and validate the endpoint layout."""
    print("FocalTech 2808:5955 USB diagnostic probe")
    print(f"  Bus/address: {getattr(device, 'bus', '?')}/{getattr(device, 'address', '?')}")
    print(f"  Vendor/product: {device.idVendor:04x}:{device.idProduct:04x}")
    bcd = device.bcdDevice
    print(f"  USB device revision (bcdDevice): {bcd >> 8:x}.{bcd & 0xff:02x}")
    print(f"  Configurations: {device.bNumConfigurations}")

    found_in = False
    found_out = False
    for configuration in device:
        print(f"  Configuration: {configuration.bConfigurationValue}")
        for interface in configuration:
            print(f"    Interface {interface.bInterfaceNumber}, alt {interface.bAlternateSetting}: "
                  f"class=0x{interface.bInterfaceClass:02x}, "
                  f"subclass=0x{interface.bInterfaceSubClass:02x}, "
                  f"protocol=0x{interface.bInterfaceProtocol:02x}")
            for endpoint in interface:
                direction = ("IN" if usb.util.endpoint_direction(endpoint.bEndpointAddress)
                             == usb.util.ENDPOINT_IN else "OUT")
                kind = usb.util.endpoint_type(endpoint.bmAttributes)
                kind_name = {0: "control", 1: "isochronous", 2: "bulk",
                             3: "interrupt"}.get(kind, "unknown")
                print(f"      0x{endpoint.bEndpointAddress:02x}: {direction}, "
                      f"{kind_name}, wMaxPacketSize={endpoint.wMaxPacketSize}")
                if (interface.bInterfaceNumber == INTERFACE
                        and interface.bAlternateSetting == 0
                        and kind == usb.util.ENDPOINT_TYPE_BULK):
                    found_in |= endpoint.bEndpointAddress == ENDPOINT_IN
                    found_out |= endpoint.bEndpointAddress == ENDPOINT_OUT

    print(f"  Expected bulk endpoints present: IN={found_in}, OUT={found_out}")
    return found_in and found_out


def is_timeout(error: usb.core.USBError) -> bool:
    return (getattr(error, "errno", None) == errno.ETIMEDOUT
            or getattr(error, "backend_error_code", None) == -7)


def listen(device: usb.core.Device, seconds: float) -> int:
    """Claim interface 0, poll only endpoint 0x82 and then release it."""
    try:
        if device.is_kernel_driver_active(INTERFACE):
            print("Interface 0 is owned by a kernel driver; refusing to detach it.",
                  file=sys.stderr)
            return 3
    except (NotImplementedError, usb.core.USBError):
        # Some backends cannot report kernel driver ownership. Never detach it.
        pass

    claimed = False
    received = 0
    print(f"[{timestamp()}] IN-only listen on endpoint 0x{ENDPOINT_IN:02x} "
          f"for {seconds:g} seconds (no commands sent).")
    print("Touch and release the fingerprint sensor during this interval.")
    try:
        usb.util.claim_interface(device, INTERFACE)
        claimed = True
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            try:
                data = device.read(ENDPOINT_IN, READ_SIZE, timeout=READ_TIMEOUT_MS)
            except usb.core.USBError as error:
                if is_timeout(error):
                    continue
                print(f"USB read error: {error}", file=sys.stderr)
                return 4
            if data:
                received += 1
                print(f"[{timestamp()}] IN {len(data)} byte(s): {bytes(data).hex(' ')}")
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
    except usb.core.USBError as error:
        print(f"USB access error: {error}", file=sys.stderr)
        print("For permissions errors, try sudo with the virtualenv Python executable.",
              file=sys.stderr)
        return 4
    finally:
        if claimed:
            try:
                usb.util.release_interface(device, INTERFACE)
            except usb.core.USBError as error:
                print(f"Warning: interface release failed: {error}", file=sys.stderr)
        usb.util.dispose_resources(device)

    print(f"[{timestamp()}] Finished. Received {received} non-empty packet(s).")
    if received == 0:
        print("No unsolicited data. The device may need protocol initialisation first.")
    else:
        print("Returned bytes may be sensitive. Do not publish raw captures.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--listen", action="store_true",
                        help="claim interface 0 temporarily and perform IN-only reads")
    parser.add_argument("--seconds", type=float, default=15.0,
                        help="listen duration (1-120 seconds; default: 15)")
    args = parser.parse_args()
    if not 1 <= args.seconds <= 120:
        parser.error("--seconds must be between 1 and 120")

    try:
        device = usb.core.find(idVendor=VID, idProduct=PID)
        if device is None:
            print("FocalTech 2808:5955 not found. Check lsusb.", file=sys.stderr)
            return 1
        endpoints_ok = describe_device(device)
        if not args.listen:
            print("Descriptor inspection finished. No data endpoints accessed.")
            return 0
        if not endpoints_ok:
            print("Expected endpoints are missing; refusing IN reads.", file=sys.stderr)
            return 3
        return listen(device, args.seconds)
    except usb.core.USBError as error:
        print(f"USB error: {error}", file=sys.stderr)
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
