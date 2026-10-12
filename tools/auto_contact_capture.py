#!/usr/bin/env python3
"""Bounded, user-authorised automatic fresh-touch acquisition for USB 2808:5955.

Runs only as a short-lived privileged *helper*, never as a GUI. It polls the
already-validated 0x82 finger-status request at most twice a second and only
retrieves an image after observing 0x06 (off) followed by 0x05 (on).
Initial contact alone does not count: release must be seen first.

At most 8 fresh-contact image reads and 240 finger-status checks (2 min).
Commands limited to tested 0x34, 0x82 73 01, 0x80 01 02, 0x81.
No 0x87, resets, autosuspend changes, uploads, image files or PAM changes.
Finger status polling itself has only been validated in isolated reads;
this intentionally limited session is experimental.

Private stdout protocol:
  type (1 byte) | size (2 bytes big endian) | data (size bytes)
  'F' = exactly 10240 bytes raw data, 'S' = ASCII state message,
  'E' = UTF-8 error, 'D' = UTF-8 end reason.
The GUI handles this pipe locally in memory. stdin 'q' or EOF stops requests.
"""
from __future__ import annotations

from dataclasses import dataclass
import os
import select
import sys
import time
from typing import Callable

from image_transfer import RAW_LENGTH, extract_image, receive_limited
from protocol_codec import ProtocolError
from scan_preflight_capture import checked_packets, decode_preflight_reply

MAX_CAPTURES = 8
MAX_STATUS_POLLS = 240
POLL_INTERVAL_S = 0.5


@dataclass
class TouchEdges:
    """Require an observed 0x06 before every subsequent 0x05 capture."""
    armed: bool = False

    def observe(self, status: int) -> str:
        if status == 0x06:
            if not self.armed:
                self.armed = True
                return "armed"
            return "off"
        if status == 0x05:
            if self.armed:
                self.armed = False
                return "capture"
            return "held"
        raise ProtocolError(f"Unexpected finger-presence status: 0x{status:02x}")


def write_record(kind: bytes, data: bytes = b"") -> None:
    if kind not in (b"F", b"S", b"E", b"D"):
        raise ValueError("Unknown private-record type")
    if kind == b"F":
        if len(data) != RAW_LENGTH:
            raise ValueError("Invalid image payload size")
    elif len(data) > 600:
        raise ValueError("Text record too large")
    sys.stdout.buffer.write(kind + len(data).to_bytes(2, "big") + data)
    sys.stdout.buffer.flush()


def cancelled() -> bool:
    """Stop when parent writes q/EOF, without changing device state."""
    readable, _, _ = select.select([sys.stdin.buffer], [], [], 0)
    if not readable:
        return False
    data = os.read(sys.stdin.buffer.fileno(), 1)
    return data == b"" or data.lower() == b"q"


def interruptible_pause(seconds: float) -> bool:
    readable, _, _ = select.select([sys.stdin.buffer], [], [], seconds)
    if not readable:
        return False
    data = os.read(sys.stdin.buffer.fileno(), 1)
    return data == b"" or data.lower() == b"q"


def scan_session(*, get_status: Callable[[], int], get_image: Callable[[], bytes],
                 report: Callable[[bytes, bytes], None],
                 should_stop: Callable[[], bool],
                 pause: Callable[[float], bool],
                 max_polls: int = MAX_STATUS_POLLS,
                 max_captures: int = MAX_CAPTURES) -> int:
    """Purely scheduled bounded loop; injection allows synthetic USB tests."""
    if not 1 <= max_polls <= MAX_STATUS_POLLS:
        raise ValueError("Invalid polling budget")
    if not 1 <= max_captures <= MAX_CAPTURES:
        raise ValueError("Invalid frame budget")
    detector = TouchEdges()
    captured = 0
    state = ""
    for _ in range(max_polls):
        if should_stop():
            report(b"D", b"Stopped by operator")
            return captured
        started = time.monotonic()
        action = detector.observe(get_status())
        if action == "armed" and state != "armed":
            report(b"S", b"Finger off: ready for a new touch")
            state = "armed"
        elif action == "held" and state != "held":
            report(b"S", b"Lift finger completely, then re-touch to acquire")
            state = "held"
        elif action == "capture":
            report(b"S", b"Fresh contact detected; acquiring one image")
            image = get_image()
            if len(image) != RAW_LENGTH:
                raise ProtocolError("Incomplete image capture")
            report(b"F", image)
            captured += 1
            state = "held"
            if captured >= max_captures:
                report(b"D", b"Eight fresh touches complete")
                return captured
            report(b"S", b"Lift your finger fully to re-arm")
        if pause(max(0.0, POLL_INTERVAL_S - (time.monotonic() - started))):
            report(b"D", b"Stopped by operator")
            return captured
    report(b"D", b"Session limit: 240 contact checks (about two minutes)")
    return captured


def hardware_session() -> int:
    try:
        import usb.core
        import usb.util
        from firmware_probe import (
            VID, PID, INTERFACE, ENDPOINT_OUT, ENDPOINT_IN,
            SEND_TIMEOUT_MS, receive_reply, validate_device,
        )
    except ImportError as exc:
        raise RuntimeError("Project Python environment is missing PyUSB") from exc

    packets = checked_packets()
    dev = usb.core.find(idVendor=VID, idProduct=PID)
    if dev is None:
        raise RuntimeError("The expected USB reader 2808:5955 is not attached")
    claimed = False
    try:
        validate_device(dev)
        usb.util.claim_interface(dev, INTERFACE)
        claimed = True

        def exchange(index: int, *, image: bool = False) -> bytes:
            packet = packets[index]
            sent = dev.write(ENDPOINT_OUT, packet, timeout=SEND_TIMEOUT_MS)
            if sent != len(packet):
                raise ProtocolError("Short USB write; stopping without retry")
            if image:
                raw = receive_limited(
                    lambda n, t: dev.read(ENDPOINT_IN, n, timeout=t),
                    seconds=10.0,
                )
            else:
                raw = receive_reply(dev)
            if not raw:
                raise ProtocolError("No USB response; stopping without retry")
            return raw

        decode_preflight_reply(exchange(0), "handshake")
        write_record(b"S", b"Handshake OK; waiting to see finger OFF")

        def get_status() -> int:
            return decode_preflight_reply(exchange(1), "finger")

        def get_image() -> bytes:
            # A new 0x05 contact event is the acquisition trigger, not 0x5aa5.
            time.sleep(0.010)
            decode_preflight_reply(exchange(2), "ready")
            return extract_image(exchange(3, image=True)).pixels

        scan_session(
            get_status=get_status, get_image=get_image,
            report=write_record, should_stop=cancelled,
            pause=interruptible_pause,
        )
        return 0
    finally:
        if claimed:
            try:
                usb.util.release_interface(dev, INTERFACE)
            except usb.core.USBError:
                print("Warning: USB interface release failed", file=sys.stderr)
        usb.util.dispose_resources(dev)


def main() -> int:
    if os.geteuid() != 0:
        print("Auto-capture helper requires sudo privileges.", file=sys.stderr)
        return 3
    try:
        return hardware_session()
    except Exception as exc:
        # Only textual diagnostics: no raw frame payload or pixel values.
        message = f"{type(exc).__name__}: {exc}".encode("utf-8", "replace")[:600]
        try:
            write_record(b"E", message)
        except BrokenPipeError:
            pass
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
