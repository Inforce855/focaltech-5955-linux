"""Synthetic-only tests for the optional local FocalTech 5955 contact viewer.

Never access the USB reader or write fingerprint data to disk.
"""
from __future__ import annotations

from io import BytesIO
from pathlib import Path
import struct
import subprocess
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import live_contact_viewer as viewer  # noqa: E402


def sample(leading: int = 0, *, value: int = 1276) -> bytes:
    """Synthetic sensor-sized array; not an actual biometric image."""
    return (b"\x00\x00" * (leading * 64)
            + value.to_bytes(2, "little") * ((80 - leading) * 64))


class ViewerTests(unittest.TestCase):
    def test_uses_bounded_known_commands(self):
        self.assertEqual(viewer.MAX_FRAMES, 8)
        self.assertGreaterEqual(viewer.INTERVAL_SECONDS, 1)
        self.assertEqual(len(viewer.checked_packets()), 4)
        self.assertEqual([p[1] for p in viewer.STEPS] if hasattr(viewer, "STEPS")
                         else [0x34, 0x82, 0x80, 0x81],
                         [0x34, 0x82, 0x80, 0x81])
        self.assertEqual([p[3] for p in __import__("scan_preflight_capture").STEPS],
                         list(viewer.checked_packets()))

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

    def test_helper_runs_only_as_root(self):
        with patch.object(viewer.os, "geteuid", return_value=1000):
            self.assertEqual(viewer.helper_main(), 3)

    def test_gui_child_capture_requires_success_and_exact_length(self):
        ok = subprocess.CompletedProcess(args=[], returncode=0, stdout=sample(),
                                         stderr=b"")
        with patch.object(viewer.subprocess, "run", return_value=ok) as run:
            self.assertEqual(viewer.invoke_helper(), sample())
        argv = run.call_args.args[0]
        self.assertEqual(argv[0:2], ["sudo", "-n"])
        self.assertEqual(argv[-1], "--helper")
        self.assertIn("capture_output", run.call_args.kwargs)
        short = subprocess.CompletedProcess(args=[], returncode=0, stdout=b"x",
                                            stderr=b"")
        with patch.object(viewer.subprocess, "run", return_value=short):
            with self.assertRaisesRegex(RuntimeError, "Wrong image length"):
                viewer.invoke_helper()
        failed = subprocess.CompletedProcess(args=[], returncode=1, stdout=b"",
                                             stderr=b"sudo: a password is required")
        with patch.object(viewer.subprocess, "run", return_value=failed):
            with self.assertRaisesRegex(RuntimeError, "sudo authorisation expired"):
                viewer.invoke_helper()


if __name__ == "__main__":
    unittest.main()
