#!/usr/bin/env python3
"""Observe a Windows-VM FocalTech 2808:5955 via Linux usbmon (read-only).

Prints only redacted command summaries, sizes, and the verified single-byte
response to Windows metadata selector 0x07. Never prints, writes, uploads,
or archives biometric image payloads or raw USB frames.

Run on Linux HOST (not in Windows guest), while VM owns the USB device:
  sudo modprobe usbmon
  lsusb -d 2808:5955
  sudo .venv/bin/python tools/windows_vm_usbmon_probe.py --seconds 90

The sensor may have been initialized before monitoring began; 0x07 will
then not necessarily appear until Windows reinitializes the driver.
"""
from __future__ import annotations

import argparse
from collections import Counter
import os
from pathlib import Path
import re
import select
import subprocess
import sys
import time

USBMON_PATH = Path("/sys/kernel/debug/usb/usbmon/0u")
LSUSB_RE = re.compile(r"^Bus\s+(\d+)\s+Device\s+(\d+):\s+ID\s+2808:5955\b", re.I)
EVENT_RE = re.compile(
    r"^\S+\s+\S+\s+([SC])\s+(B[io]):(\d+):(\d+):(\d+)\s+"
    r"(-?\d+)\s+(\d+)\s*(.*)$"
)

MAX_SMALL_RESPONSE = 16
MAX_COMMAND_BYTES = 32


def usb_location() -> tuple[int, int]:
    try:
        result = subprocess.run(
            ["lsusb", "-d", "2808:5955"], capture_output=True, text=True,
            timeout=5, check=True
        )
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError("Run 'lsusb -d 2808:5955' to locate the USB reader") from exc
    found = [tuple(int(v) for v in match.groups())
             for line in result.stdout.splitlines()
             if (match := LSUSB_RE.search(line))]
    if len(found) != 1:
        raise RuntimeError("Expected exactly one 2808:5955 USB device; "
                           "check the USB pass-through or provide --bus and --device")
    return found[0]


def hex_payload(tail: str, cap: int) -> bytes:
    """Parse the usbmon '= hex' marker; cap means NEVER decode large data."""
    if "=" not in tail:
        return b""
    encoded = tail.partition("=")[2].strip()
    if not re.fullmatch(r"[\da-fA-F\s]*", encoded):
        return b""
    encoded = re.sub(r"\s+", "", encoded)
    if len(encoded) % 2 or len(encoded) > cap * 2:
        return b""
    try:
        return bytes.fromhex(encoded)
    except ValueError:
        return b""


def validated_small_reply(frame: bytes) -> bytes | None:
    """Protocol: 02 | BE16 size | 04 | payload | XOR, optional one trailer."""
    if len(frame) < 5 or frame[0] != 2:
        return None
    declared = int.from_bytes(frame[1:3], "big")
    total = 3 + declared + 1
    if not 2 <= declared <= MAX_SMALL_RESPONSE - 4:
        return None
    if len(frame) not in (total, total + 1) or frame[3] != 0x04:
        return None
    checksum = 0
    for value in frame[1:-1] if len(frame) == total else frame[1:-2]:
        checksum ^= value
    if frame[total - 1] != checksum:
        return None
    return frame[4:total-1]


class RedactedMonitor:
    def __init__(self, bus: int, device: int):
        self.bus = bus
        self.device = device
        self.commands: Counter[int] = Counter()
        self.image_reads = 0
        self.request_07 = 0
        self.flag_07 = None
        self.flag_pending = False
        self.small_replies = 0
        self.image_transfers = 0

    def accept(self, line: str) -> list[str]:
        match = EVENT_RE.match(line.strip())
        if not match:
            return []
        stage, direction, bus, device, endpoint, status, size, tail = match.groups()
        if int(bus) != self.bus or int(device) != self.device:
            return []
        size = int(size)
        if stage == "S" and direction == "Bo":
            # The Windows command frame is <=32 bytes; no image is sent OUT.
            if size < 5 or size > MAX_COMMAND_BYTES:
                return ["USB OUT (large transfer; data withheld)"]
            message = hex_payload(tail, MAX_COMMAND_BYTES)
            if len(message) < 5 or message[0] != 0x02:
                return ["USB OUT request (unparsed; data withheld)"]
            length = int.from_bytes(message[1:3], "big")
            if length + 4 != len(message):
                return ["USB OUT request (incomplete; data withheld)"]
            expected = 0
            for value in message[1:-1]:
                expected ^= value
            if expected != message[-1]:
                return ["USB OUT request (invalid framing/checksum; data withheld)"]
            command, parameters = message[3], message[4:-1]
            self.commands[command] += 1
            if command == 0x81:
                self.image_reads += 1
                return ["Windows requested a fingerprint image (0x81)"]
            if command == 0x80:
                selector = parameters[0] if parameters else None
                if selector == 0x07 and len(parameters) >= 2:
                    self.request_07 += 1
                    self.flag_pending = True
                    return ["Windows queried image-processing mode (0x80 selector 0x07)"]
                return [f"Windows metadata read (0x80 selector "
                        f"{'0x%02x' % selector if selector is not None else 'unknown'})"]
            if command == 0x87:
                return [f"Windows mode-control command 0x87 ({len(parameters)} parameter bytes; redacted)"]
            return [f"Windows command 0x{command:02x} ({len(parameters)} parameter bytes; redacted)"]
        if stage == "C" and direction == "Bi":
            # Fingerprint images can be 10240+ bytes. Do NOT decode their data.
            if size > MAX_SMALL_RESPONSE:
                self.image_transfers += 1
                return [f"USB IN large transfer ({size} bytes; biometric data REDACTED)"]
            if size < 5:
                return []
            small = hex_payload(tail, MAX_SMALL_RESPONSE)
            if len(small) != size:
                return []
            payload = validated_small_reply(small)
            if payload is None:
                return []
            self.small_replies += 1
            if self.flag_pending:
                self.flag_pending = False
                if len(payload) == 1 and payload[0] in (0, 1):
                    self.flag_07 = payload[0]
                    return [f"CONFIRMED 0x07 MODE FLAG: {payload[0]} "
                            f"({'conditional decrypt enabled' if payload[0] else 'conditional decrypt bypassed'})"]
                return ["Metadata response after selector 0x07 was not a confirmed 0/1 flag"]
        return []

    def summary(self) -> list[str]:
        values = ", ".join(f"0x{k:02x}={v}" for k, v in sorted(self.commands.items()))
        return [
            "Windows VM USB observation summary:",
            f"  Request counts: {values or 'none observed'}",
            f"  0x81 image requests: {self.image_reads}",
            f"  Large USB IN transfers: {self.image_transfers} (contents always redacted)",
            f"  0x07 selector requests: {self.request_07}",
            "  0x07 mode flag: " +
            (str(self.flag_07) if self.flag_07 is not None else
             "NOT OBSERVED (possibly initialized before monitoring)"),
            "  No image/biometric bytes were printed or saved.",
        ]


def observe(monitor: RedactedMonitor, seconds: int, path: Path = USBMON_PATH) -> None:
    if not path.is_file():
        raise RuntimeError(f"{path} is unavailable. Run 'sudo modprobe usbmon' "
                           "and check debugfs at /sys/kernel/debug")
    print(f"Monitoring physical 2808:5955 at USB bus {monitor.bus}, "
          f"device {monitor.device} for up to {seconds} seconds.")
    print("Use your Windows VM normally. One successful Windows Hello touch is enough.")
    print("ONLY redacted metadata and command identifiers will be printed. Ctrl+C ends capture.")
    sys.stdout.flush()
    end = time.monotonic() + seconds
    partial = b""
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
    try:
        while time.monotonic() < end:
            ready, _, _ = select.select([fd], [], [], min(0.5, max(0.0, end - time.monotonic())))
            if not ready:
                continue
            try:
                chunk = os.read(fd, 65536)
            except BlockingIOError:
                continue
            if not chunk:
                continue
            partial += chunk
            lines = partial.split(b"\n")
            partial = lines.pop()
            if len(partial) > 4096:  # cap potentially malformed stream
                partial = b""
            for line in lines:
                for message in monitor.accept(line.decode("ascii", "replace")):
                    print(message, flush=True)
    except KeyboardInterrupt:
        print("\nMonitoring stopped by operator.")
    finally:
        os.close(fd)
        print("\n" + "\n".join(monitor.summary()))


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--seconds", type=int, default=90)
    p.add_argument("--bus", type=int)
    p.add_argument("--device", type=int)
    args = p.parse_args()
    if not 1 <= args.seconds <= 600:
        p.error("--seconds must be 1..600")
    if (args.bus is None) != (args.device is None):
        p.error("--bus and --device must be used together")
    try:
        bus, device = (args.bus, args.device) if args.bus is not None else usb_location()
        if not (1 <= bus <= 255 and 1 <= device <= 127):
            p.error("Invalid USB bus/device values")
        observe(RedactedMonitor(bus, device), args.seconds)
        return 0
    except (RuntimeError, PermissionError, OSError) as exc:
        print(f"USB monitoring unavailable: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
