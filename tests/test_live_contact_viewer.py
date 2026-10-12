"""Synthetic-only tests for the optional local FocalTech 5955 contact viewer.

Never access the USB reader or write fingerprint data to disk.
"""
from __future__ import annotations

from pathlib import Path
import struct
import subprocess
import sys
from types import ModuleType
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
        self.assertGreaterEqual(viewer.MIN_REQUEST_INTERVAL_SECONDS, 1)
        self.assertEqual(len(viewer.checked_packets()), 4)
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


    def test_eight_touch_session_never_scans_on_timer_or_retries_automatically(self):
        class Widget:
            def __init__(self, *args, **kwargs):
                self.options = dict(kwargs)
            def grid(self, **kwargs):
                pass
            def pack(self, **kwargs):
                pass
            def configure(self, **kwargs):
                self.options.update(kwargs)
        class Variable:
            def __init__(self, value=""):
                self.value = value
            def set(self, value):
                self.value = value
            def get(self):
                return self.value
        class Root:
            def __init__(self):
                self.destroyed = False
            def title(self, value):
                pass
            def resizable(self, *args):
                pass
            def protocol(self, *args):
                pass
            def after(self, *args):
                pass
            def destroy(self):
                self.destroyed = True

        tk = ModuleType("tkinter")
        ttk = ModuleType("tkinter.ttk")
        tk.Label = Widget
        tk.StringVar = Variable
        tk.PhotoImage = Widget
        ttk.Label = ttk.Frame = ttk.Button = Widget
        tk.ttk = ttk
        modules = {"tkinter": tk, "tkinter.ttk": ttk}
        with patch.dict(sys.modules, modules):
            root = Root()
            gui = viewer.ContactViewer(root, enabled=True)
            with patch.object(viewer.threading, "Thread") as mock_thread:
                gui.begin_session()
                self.assertEqual(mock_thread.call_count, 1)
                self.assertEqual(gui.session_limit, 8)
                self.assertTrue(gui.working)

                # A completed first scan does NOT automatically queue frame 2.
                gui.mailbox.put(("frame", sample()))
                gui.mailbox.put(("done",))
                gui.drain()
                self.assertEqual(gui.session_taken, 1)
                self.assertFalse(gui.working)
                self.assertEqual(mock_thread.call_count, 1)
                self.assertIn("LIFT", gui.message.get())
                self.assertEqual(gui.next_btn.options["state"], "normal")

                # Operator clicks too early, while finger is absent.
                # Keep previous image and allow an explicit new attempt.
                gui.last_started = 0.0
                gui.next_capture()
                self.assertEqual(mock_thread.call_count, 2)
                gui.mailbox.put(("error", "Capture stopped: RuntimeError: No finger detected (status 0x06); no image read"))
                gui.mailbox.put(("done",))
                gui.drain()
                self.assertEqual(gui.session_taken, 1)
                self.assertEqual(gui.session_limit, 8)
                self.assertEqual(mock_thread.call_count, 2)
                self.assertIn("Re-touch", gui.message.get())

                # Operator re-touches, and must explicitly click again.
                gui.last_started = 0.0
                gui.next_capture()
                self.assertEqual(mock_thread.call_count, 3)
                gui.mailbox.put(("frame", sample(2)))
                gui.mailbox.put(("done",))
                gui.drain()
                self.assertEqual(gui.session_taken, 2)
                self.assertEqual(mock_thread.call_count, 3)
                gui.stop()
                self.assertEqual(gui.session_limit, 0)
                self.assertEqual(gui.next_btn.options["state"], "disabled")
                self.assertEqual(mock_thread.call_count, 3)
                gui.close()
                self.assertTrue(root.destroyed)

    def test_click_rate_limit_does_not_schedule_usb(self):
        class FakeThread:
            starts = 0
            def __init__(self, *args, **kwargs):
                pass
            def start(self):
                self.starts += 1
        class MinimalGUI:
            working = False
            stopping = False
            enabled = True
            last_started = 100.0
            def __init__(self):
                self.message = type("Message", (), {"set": lambda s, msg: setattr(s, "value", msg)})()
                self.updated = False
            def update_controls(self):
                self.updated = True
        gui = MinimalGUI()
        with patch.object(viewer.time, "monotonic", return_value=100.3), \
             patch.object(viewer.threading, "Thread", FakeThread):
            result = viewer.ContactViewer.request_frame(gui)
        self.assertFalse(result)
        self.assertFalse(gui.working)
        self.assertIn("at least one second", gui.message.value)


if __name__ == "__main__":
    unittest.main()
