"""Synthetic-only preflight test for FocalTech 5955. No real USB access."""
from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from protocol_codec import ProtocolError, xor_bcc  # noqa: E402
from scan_preflight_capture import (  # noqa: E402
    STEPS, checked_packets, count_blank_rows, decode_preflight_reply,
    main, run_live,
)


def response(payload: bytes) -> bytes:
    body = (len(payload) + 1).to_bytes(2, "big") + b"\x04" + payload
    return b"\x02" + body + bytes([xor_bcc(body)]) + b"\x00"


def fake_modules(responses: list[bytes]):
    """Stub USB stack, record commands, and prevent all real device access."""
    sent = []
    dev = SimpleNamespace(
        write=lambda ep, data, timeout: (sent.append(bytes(data)) or len(data)),
        read=lambda ep, count, timeout: b"",
    )
    usb = ModuleType("usb")
    usb.__path__ = []
    core = ModuleType("usb.core")
    core.USBError = type("USBError", (Exception,), {})
    core.find = lambda **kwargs: dev
    util = ModuleType("usb.util")
    util.claim_interface = lambda *args: None
    util.release_interface = lambda *args: None
    util.dispose_resources = lambda *args: None
    usb.core = core
    usb.util = util
    firmware = ModuleType("firmware_probe")
    firmware.ENDPOINT_IN = 0x82
    firmware.ENDPOINT_OUT = 0x01
    firmware.INTERFACE = 0
    firmware.PID = 0x5955
    firmware.SEND_TIMEOUT_MS = 1000
    firmware.SafetyAbort = type("SafetyAbort", (Exception,), {})
    firmware.VID = 0x2808
    firmware.receive_reply = lambda device: responses.pop(0)
    firmware.timed_out = lambda e: False
    firmware.validate_device = lambda device: None
    return sent, {"usb": usb, "usb.core": core, "usb.util": util,
                  "firmware_probe": firmware}


class PreflightTests(unittest.TestCase):
    def test_all_four_audited_command_bytes(self):
        self.assertEqual(checked_packets(), tuple(p[3] for p in STEPS))
        self.assertEqual([p[1] for p in STEPS], [0x34, 0x82, 0x80, 0x81])
        self.assertNotIn(0x87, [p[1] for p in STEPS])

    def test_reply_markers_and_integrity(self):
        self.assertEqual(decode_preflight_reply(response(b"\x55\xaa"), "handshake"), 0xAA55)
        self.assertEqual(decode_preflight_reply(response(b"\x05"), "finger"), 0x05)
        self.assertEqual(decode_preflight_reply(response(b"\x06"), "finger"), 0x06)
        self.assertEqual(decode_preflight_reply(response(b"\xa5\x5a"), "ready"), 0x5AA5)
        with self.assertRaises(ProtocolError):
            decode_preflight_reply(response(b"\x06"), "ready")
        bad = bytearray(response(b"\x55\xaa"))
        bad[-2] ^= 1
        with self.assertRaises(ProtocolError):
            decode_preflight_reply(bytes(bad), "handshake")

    def test_blank_row_counts(self):
        data = b"\x00\x00" * (16 * 64) + b"\xe8\x03" * (64 * 64)
        self.assertEqual(count_blank_rows(data), (16, 16, 0, 20.0))
        data = b"\xe8\x03" * (75 * 64) + b"\x00\x00" * (5 * 64)
        self.assertEqual(count_blank_rows(data), (0, 5, 5, 6.25))
        with self.assertRaises(ValueError):
            count_blank_rows(b"")

    def test_dry_run_sends_no_commands(self):
        output = StringIO()
        with patch.object(sys, "argv", ["scan_preflight_capture.py"]), redirect_stdout(output):
            self.assertEqual(main(), 0)
        self.assertIn("DRY RUN", output.getvalue())

    def test_absent_finger_aborts_before_ready_or_image(self):
        sent, mods = fake_modules([response(b"\x55\xaa"), response(b"\x06")])
        with (patch.dict(sys.modules, mods), patch("scan_preflight_capture.time.sleep"),
              redirect_stdout(StringIO())):
            status = run_live(checked_packets())
        self.assertEqual(status, 5)
        self.assertEqual(sent, list(checked_packets()[:2]))

    def test_successful_mock_image_has_no_unapproved_requests(self):
        sent, mods = fake_modules([
            response(b"\x55\xaa"), response(b"\x05"),
            response(b"\xa5\x5a"),
        ])
        fake_raw = b"\x00\x00" * (16 * 64) + b"\xe8\x03" * (64 * 64)
        frame = response(fake_raw)
        saved = []
        output = StringIO()
        with (patch.dict(sys.modules, mods),
              patch("scan_preflight_capture.receive_limited", return_value=frame),
              patch("scan_preflight_capture.save_private_raw",
                    side_effect=lambda b: (saved.append(bytes(b)) or Path("local-data/synthetic.raw"))),
              patch("scan_preflight_capture.time.sleep"),
              redirect_stdout(output)):
            result = run_live(checked_packets())
        self.assertEqual(result, 0)
        self.assertEqual(sent, list(checked_packets()))
        self.assertEqual(saved, [fake_raw])
        self.assertIn("leading blank rows: 16", output.getvalue())
        self.assertIn("IMAGE QUALITY WARNING", output.getvalue())


if __name__ == "__main__":
    unittest.main()
