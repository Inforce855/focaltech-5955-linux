"""Offline state-machine checks for bounded 5955 contact acquisition."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from auto_contact_capture import TouchEdges, scan_session, MAX_CAPTURES, MAX_STATUS_POLLS
from protocol_codec import ProtocolError

SYNTHETIC = b"\xe8\x03" * 5120


class AutomaticCaptureTests(unittest.TestCase):
    def test_edges(self):
        edge = TouchEdges()
        self.assertEqual([edge.observe(v) for v in [5, 5, 6, 6, 5, 5, 6, 5]],
                         ["held", "held", "armed", "off", "capture",
                          "held", "armed", "capture"])

    def test_bad_status(self):
        with self.assertRaises(ProtocolError):
            TouchEdges().observe(0xff)

    def test_release_required_and_no_repeat(self):
        statuses = iter([5, 5, 6, 5, 5, 5, 6, 5])
        images = []
        events = []
        count = scan_session(
            get_status=lambda: next(statuses),
            get_image=lambda: (images.append(1) or SYNTHETIC),
            report=lambda kind, payload: events.append(kind),
            should_stop=lambda: False,
            pause=lambda seconds: False,
            max_polls=8,
        )
        self.assertEqual(count, 2)
        self.assertEqual(len(images), 2)
        self.assertEqual(events.count(b"F"), 2)

    def test_absent_never_reads_image(self):
        count = scan_session(
            get_status=lambda: 6,
            get_image=lambda: self.fail("Unexpected image read"),
            report=lambda kind, data: None,
            should_stop=lambda: False,
            pause=lambda seconds: False,
            max_polls=5,
        )
        self.assertEqual(count, 0)

    def test_eight_scans_is_hard_limit(self):
        statuses = iter([6, 5] * 9)
        count = scan_session(
            get_status=lambda: next(statuses),
            get_image=lambda: SYNTHETIC,
            report=lambda kind, payload: None,
            should_stop=lambda: False,
            pause=lambda seconds: False,
            max_polls=30,
            max_captures=MAX_CAPTURES,
        )
        self.assertEqual(count, 8)
        self.assertEqual(MAX_STATUS_POLLS, 240)

    def test_operator_stop_before_first_read(self):
        scans = []
        result = scan_session(
            get_status=lambda: scans.append(1) or 6,
            get_image=lambda: self.fail("Unexpected image read"),
            report=lambda kind, data: None,
            should_stop=lambda: True,
            pause=lambda seconds: False,
            max_polls=6,
        )
        self.assertEqual(result, 0)
        self.assertFalse(scans)


if __name__ == "__main__":
    unittest.main()
