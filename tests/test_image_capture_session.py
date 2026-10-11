"""All tests are OFFLINE; no USB connections or actual biometric samples."""
from __future__ import annotations

import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from image_capture_probe import (
    CAPTURE_SEQUENCE, RAW_LENGTH, run_session, save_private_raw, wait_for_enter,
)


class CaptureSessionTests(unittest.TestCase):
    def test_labels_and_sequence(self):
        self.assertEqual(tuple(label for label, _ in CAPTURE_SEQUENCE),
                         ("A1", "A2", "B1", "B2"))

    def test_four_enters_send_exactly_four_labelled_requests(self):
        calls = []
        def capture(*, label):
            calls.append(label)
            return 0
        inputs = iter(("", "", "", ""))
        result = run_session(capture_fn=capture, input_fn=lambda _: next(inputs))
        self.assertEqual(result, 0)
        self.assertEqual(calls, ["A1", "A2", "B1", "B2"])

    def test_cancel_before_first_capture_sends_nothing(self):
        capture = Mock()
        result = run_session(capture_fn=capture, input_fn=lambda _: "q")
        self.assertEqual(result, 3)
        capture.assert_not_called()

    def test_cancel_after_first_keeps_single_capture(self):
        calls = []
        prompts = iter(("", "q"))
        def capture(*, label):
            calls.append(label)
            return 0
        result = run_session(capture_fn=capture, input_fn=lambda _: next(prompts))
        self.assertEqual(result, 3)
        self.assertEqual(calls, ["A1"])

    def test_failure_stops_session_without_retries(self):
        calls = []
        def capture(*, label):
            calls.append(label)
            return 6 if label == "A2" else 0
        result = run_session(capture_fn=capture, input_fn=lambda _: "")
        self.assertEqual(result, 6)
        self.assertEqual(calls, ["A1", "A2"])

    def test_ctrl_c_during_prompt_sends_nothing(self):
        capture = Mock()
        def interrupt(_):
            raise KeyboardInterrupt
        result = run_session(capture_fn=capture, input_fn=interrupt)
        self.assertEqual(result, 3)
        capture.assert_not_called()

    def test_return_requires_exact_empty_enter(self):
        self.assertTrue(wait_for_enter("test", input_fn=lambda _: ""))
        self.assertFalse(wait_for_enter("test", input_fn=lambda _: " "))
        self.assertFalse(wait_for_enter("test", input_fn=lambda _: "CAPTURE"))
        self.assertFalse(wait_for_enter("test", input_fn=lambda _: "SEND"))

    def test_private_labelled_file_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch("image_capture_probe.private_output_folder", return_value=Path(tmp)):
                samples = bytes(RAW_LENGTH)  # synthetic, not a fingerprint
                with patch.dict(os.environ, {"SUDO_UID": str(os.getuid()),
                                              "SUDO_GID": str(os.getgid())}):
                    result = save_private_raw(samples, label="B2")
                    self.assertTrue(result.name.endswith("_B2.raw"))
                    self.assertEqual(result.read_bytes(), samples)
                    self.assertEqual(stat.S_IMODE(result.stat().st_mode), 0o600)
                    with self.assertRaises(FileExistsError):
                        save_private_raw(samples, label="B2")

    def test_unsafe_labels_rejected_without_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch("image_capture_probe.private_output_folder", return_value=Path(tmp)):
                with self.assertRaises(ValueError):
                    save_private_raw(bytes(RAW_LENGTH), label="../outside")
                self.assertEqual(list(Path(tmp).iterdir()), [])


if __name__ == "__main__":
    unittest.main()
