"""Source-only FT5955 identify overlay checks; NO USB, PAM, biometric data."""
from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from ft5955_identify_overlay import ACTION, DRIVER, HEADER, apply_identify_variant

SNAP = ROOT / "driver" / "live-snapshot-2026-10-16"


class IdentifySourceOverlayTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="ft5955-identify-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "libfprint-source"
        self.root.mkdir()
        self.original: dict[Path, bytes] = {}
        for path in (ACTION, DRIVER, HEADER):
            dest = self.root / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            data = (SNAP / path).read_bytes()
            self.original[path] = data
            dest.write_bytes(data)

    def test_single_capture_gallery_and_result_contract(self):
        apply_identify_variant(self.root)
        action = (self.root / ACTION).read_text()
        cls = (self.root / DRIVER).read_text()
        hdr = (self.root / HEADER).read_text()
        self.assertIn("dev_class->verify = ft5955_native_verify;", cls)
        self.assertIn("dev_class->identify = ft5955_native_identify;", cls)
        self.assertIn("void ft5955_native_identify(FpDevice *device);", hdr)
        self.assertEqual(action.count("ft5955_native_scan (job->usb, c, frame, &err)"), 1)
        capture = action.index("ft5955_native_scan (job->usb, c, frame, &err)")
        gallery = action.index("for (guint i = 0; i < job->length; i++)", capture)
        matcher = action.index("ft5955_identify_try (", gallery)
        self.assertLess(capture, gallery)
        self.assertLess(gallery, matcher)
        for marker in (
            'strcmp (reply, "MATCH")',
            'strcmp (reply, "NO_MATCH")',
            'strcmp (reply, "RETRY QUALITY")',
            'fpi_device_get_identify_data (dev, &gallery)',
            "ft5955_fpprint_extract (print, &job->templates[i])",
            "fpi_device_identify_report (dev, match, NULL, NULL)",
            "fpi_device_identify_complete (dev, NULL)",
            "job->match_index = -1",
            "sensitive_clear (frame, sizeof frame)",
            "ft5955_print_template_clear (&job->templates[i])",
            "g_task_set_return_on_cancel (task, FALSE)",
            "FT5955_MAX_IDENTIFY_GALLERY",
            "FT5955_MAX_IDENTIFY_CAPTURE",
            "g_cancellable_set_error_if_cancelled",
        ):
            self.assertIn(marker, action)
        # The source-only overlay must preserve the previous verify entry point.
        self.assertIn("void ft5955_native_verify(FpDevice *dev) { launch(dev,FALSE); }", action)

    def test_snapshot_unchanged_and_no_repeat_application(self):
        before = {
            path: hashlib.sha256((SNAP / path).read_bytes()).hexdigest()
            for path in self.original
        }
        apply_identify_variant(self.root)
        with self.assertRaisesRegex(ValueError, "Unexpected identify source anchor"):
            apply_identify_variant(self.root)
        for path, digest in before.items():
            self.assertEqual(hashlib.sha256((SNAP / path).read_bytes()).hexdigest(), digest)

    def test_all_anchors_preflighted_before_any_changes(self):
        header = self.root / HEADER
        header.write_text("invalid source header")
        with self.assertRaisesRegex(ValueError, "Unexpected identify source anchor"):
            apply_identify_variant(self.root)
        self.assertEqual((self.root / ACTION).read_bytes(), self.original[ACTION])
        self.assertEqual((self.root / DRIVER).read_bytes(), self.original[DRIVER])

    def test_reject_symlinked_sources(self):
        driver = self.root / DRIVER
        driver.unlink()
        driver.symlink_to(SNAP / DRIVER)
        with self.assertRaisesRegex(ValueError, "Missing regular identify target"):
            apply_identify_variant(self.root)
        self.assertEqual((self.root / ACTION).read_bytes(), self.original[ACTION])


if __name__ == "__main__":
    unittest.main()
