"""Synthetic-only tests for the automatic FocalTech 5955 contact viewer.

No GUI display, real USB I/O, biometric data or filesystem writes.
"""
from __future__ import annotations

from io import BytesIO
from pathlib import Path
import struct
import subprocess
import sys
import threading
import unittest
from unittest.mock import patch
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import live_contact_viewer as viewer  # noqa: E402


def sample(leading: int = 0, *, value: int = 1276) -> bytes:
    """Artificial constant image, NOT an actual fingerprint."""
    return (b"\x00\x00" * (leading * 64)
            + value.to_bytes(2, "little") * ((80 - leading) * 64))


class ViewerTests(unittest.TestCase):
    def test_zero_band_stats_for_synthetic_data(self):
        details = viewer.frame_statistics(sample(16))
        self.assertEqual(details["zeros"], 20.0)
        self.assertEqual(details["leading"], 16)
        self.assertEqual(details["all_rows"], 16)
        self.assertEqual(details["trailing"], 0)
        self.assertEqual(details["top"], 80.0)
        self.assertEqual(details["middle"], 0.0)
        self.assertEqual(details["bottom"], 0.0)

    def test_two_private_in_memory_previews(self):
        image, mask = viewer.preview_pngs(sample(16))
        self.assertTrue(image.startswith(b"\x89PNG\r\n\x1a\n"))
        self.assertTrue(mask.startswith(b"\x89PNG\r\n\x1a\n"))
        self.assertEqual(struct.unpack_from(">II", image, 16), (384, 480))
        self.assertEqual(struct.unpack_from(">II", mask, 16), (384, 480))
        self.assertNotEqual(image, mask)

    def test_reject_incorrect_length(self):
        with self.assertRaises(ValueError):
            viewer.frame_statistics(b"")
        with self.assertRaises(ValueError):
            viewer.preview_pngs(b"")

    def test_read_local_helper_protocol_multiple_records(self):
        source = BytesIO(
            b"S" + (5).to_bytes(2, "big") + b"ready" +
            b"F" + (10240).to_bytes(2, "big") + sample(2) +
            b"D" + (4).to_bytes(2, "big") + b"done"
        )
        self.assertEqual(viewer.read_record(source), (b"S", b"ready"))
        self.assertEqual(viewer.read_record(source), (b"F", sample(2)))
        self.assertEqual(viewer.read_record(source), (b"D", b"done"))
        self.assertIsNone(viewer.read_record(source))

    def test_truncated_or_oversized_records_fail_closed(self):
        with self.assertRaises(EOFError):
            viewer.read_record(BytesIO(b"F\x28\x00" + b"x" * 10))
        with self.assertRaises(ValueError):
            viewer.read_record(BytesIO(b"F\x00\x08abcdefgh"))
        with self.assertRaises(ValueError):
            viewer.read_record(BytesIO(b"S\xff\xff"))
        with self.assertRaises(ValueError):
            viewer.read_record(BytesIO(b"Q\x00\x00"))

    def test_stopping_sends_q_to_privileged_helper(self):
        writes = BytesIO()
        gui = viewer.ContactViewer.__new__(viewer.ContactViewer)
        gui.stopping = threading.Event()
        gui.message = SimpleNamespace(set=lambda text: None)
        gui.proc = SimpleNamespace(stdin=writes)
        gui.stop()
        self.assertTrue(gui.stopping.is_set())
        self.assertEqual(writes.getvalue(), b"q")

    def test_start_autoscanning_needs_no_capture_click(self):
        gui = viewer.ContactViewer.__new__(viewer.ContactViewer)
        gui.running = False
        gui.closed = False
        gui.enabled = True
        gui.frames = 4
        gui.stopping = threading.Event()
        messages = []
        gui.message = SimpleNamespace(set=lambda text: messages.append(text))
        gui.update_buttons = lambda: None
        with patch.object(viewer.threading, "Thread") as thread:
            gui.start()
        self.assertTrue(gui.running)
        self.assertEqual(gui.frames, 0)
        self.assertTrue(thread.called)
        self.assertIn("Lift your finger", messages[-1])

    def test_stop_before_helper_launch_sends_no_usb(self):
        gui = viewer.ContactViewer.__new__(viewer.ContactViewer)
        gui.stopping = threading.Event()
        gui.stopping.set()
        gui.mailbox = __import__("queue").Queue()
        gui.proc = None
        with patch.object(viewer.subprocess, "Popen") as launch:
            gui.worker()
        launch.assert_not_called()
        self.assertEqual(gui.mailbox.get_nowait()[0], "done")


if __name__ == "__main__":
    unittest.main()
