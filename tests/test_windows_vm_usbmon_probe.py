"""Synthetic-only regression tests of redacted Windows VM USB monitoring.

No USB, Windows VM, hardware access, real packets or biometrics.
"""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from windows_vm_usbmon_probe import RedactedMonitor, validated_small_reply


class UsbmonProbeTests(unittest.TestCase):
    def setUp(self):
        self.m = RedactedMonitor(1, 5)

    def test_windows_selector07_reply(self):
        # 02 00 03 80 07 01 85: 0x80 metadata selector 7, length 1.
        sent = self.m.accept("a 100 S Bo:1:005:1 -115 7 = 02000380070185")
        self.assertIn("0x07", sent[0])
        received = self.m.accept("b 101 C Bi:1:005:2 0 7 = 02000204010700")
        self.assertIn("CONFIRMED", received[0])
        self.assertEqual(self.m.flag_07, 1)

    def test_flag_disabled(self):
        self.m.accept("a 100 S Bo:1:005:1 -115 7 = 02000380070185")
        self.m.accept("b 101 C Bi:1:005:2 0 7 = 02000204000600")
        self.assertEqual(self.m.flag_07, 0)

    def test_wrong_device_ignored(self):
        self.assertEqual(
            self.m.accept("a 100 S Bo:1:004:1 -115 7 = 02000380070185"), []
        )
        self.assertEqual(self.m.request_07, 0)

    def test_no_biometric_bytes_printed(self):
        self.m.accept("a 100 S Bo:1:005:1 -115 5 = 0200018180")
        # Large IN payload might contain a full raw fingerprint;
        # it MUST remain entirely redacted even if a hex payload follows.
        notes = self.m.accept(
            "b 101 C Bi:1:005:2 0 10246 = "
            "0200280400aabbccddeeff0102030405"
        )
        self.assertEqual(len(notes), 1)
        self.assertIn("REDACTED", notes[0])
        self.assertNotIn("aabb", notes[0])
        self.assertEqual(self.m.image_reads, 1)

    def test_bad_reply_checksum_not_accepted(self):
        self.m.accept("a 100 S Bo:1:005:1 -115 7 = 02000380070185")
        self.assertEqual(
            self.m.accept("b 101 C Bi:1:005:2 0 7 = 02000204010000"),
            []
        )
        self.assertIsNone(self.m.flag_07)

    def test_optional_trailing_usb_byte(self):
        self.assertEqual(validated_small_reply(bytes.fromhex("02000204010700")), b"\x01")
        self.assertEqual(validated_small_reply(bytes.fromhex("020002040107")), b"\x01")

    def test_bad_usb_frame(self):
        self.assertIsNone(validated_small_reply(b"garbage"))

    def test_unfamiliar_command_parameter_redacted(self):
        # 0x90 and one parameter 0xde; checksum 02^90^de = 4c.
        notes = self.m.accept("a 100 S Bo:1:005:1 -115 6 = 02000290de4c")
        self.assertIn("redacted", notes[0])
        self.assertNotIn("de", notes[0])

    def test_repeated_windows_hello_polls_do_not_spam(self):
        status_query = "a 100 S Bo:1:005:1 -115 7 = 02000380020180"
        # Command BCC: 03 ^ 80 ^ 02 ^ 01 = 80
        gpio_set = "a 101 S Bo:1:005:1 -115 8 = 0200043701010132"
        status_reply_zero = "a 102 C Bi:1:005:2 0 7 = 02000204000600"
        first = self.m.accept(status_query)
        self.assertIn("polling", first[0])
        self.assertEqual(len(self.m.accept(gpio_set)), 1)
        self.assertEqual(self.m.accept(gpio_set), [])
        self.assertEqual(self.m.accept(status_reply_zero), ["Windows finger-status BYTE changed to 0x00 (meaning not yet inferred)"])
        for _ in range(100):
            self.assertEqual(self.m.accept(status_query), [])
            self.assertEqual(self.m.accept(status_reply_zero), [])
            self.assertEqual(self.m.accept(gpio_set), [])
        self.assertEqual(self.m.status_queries, 101)
        self.assertEqual(self.m.gpio_requests, 102)
        self.assertEqual(self.m.status_changes, 1)

    def test_finger_status_changes_reported_once(self):
        poll = "a 100 S Bo:1:005:1 -115 7 = 02000380020180"
        off = "a 101 C Bi:1:005:2 0 7 = 02000204000600"
        on = "a 102 C Bi:1:005:2 0 7 = 02000204010700"
        self.m.accept(poll)
        self.m.accept(off)
        self.m.accept(poll)
        lines = self.m.accept(on)
        self.assertIn("0x01", lines[0])
        self.assertEqual(self.m.status_changes, 2)


if __name__ == "__main__":
    unittest.main()
