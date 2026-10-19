"""Offline FT5955 identify v2 source and timing regression (NO USB, no PAM)."""
from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from ft5955_identify_overlay import ACTION, DRIVER, HEADER, apply_identify_variant
from ft5955_identify_overlay_v2 import apply_identify_v2_variant
from verify_ft5955_clean_clone import (
    CAPTURE_SOURCE,
    apply_poll100_variant,
    apply_earlycapture_variant,
    apply_timingtrace_variant,
)

SNAP = ROOT / "driver" / "live-snapshot-2026-10-16"
FILES = (ACTION, DRIVER, HEADER, Path(CAPTURE_SOURCE))


class IdentifyV2Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="ft5955-identify-v2-")
        self.addCleanup(self.tmp.cleanup)
        self.source = Path(self.tmp.name) / "libfprint-source"
        self.source.mkdir()
        self.snap_hashes = {}
        for relative in FILES:
            original = SNAP / relative
            destination = self.source / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            data = original.read_bytes()
            destination.write_bytes(data)
            self.snap_hashes[relative] = hashlib.sha256(data).hexdigest()

    def apply_v1(self):
        apply_poll100_variant(self.source)
        apply_earlycapture_variant(self.source)
        apply_timingtrace_variant(self.source)
        apply_identify_variant(self.source)

    def test_v2_retries_other_templates_using_one_image(self):
        self.apply_v1()
        before = (self.source / ACTION).read_text()
        apply_identify_v2_variant(self.source)
        code = (self.source / ACTION).read_text()
        self.assertIn("dev_class->identify", (self.source / DRIVER).read_text())
        self.assertEqual(code.count("ft5955_native_scan (job->usb, c, frame, &err)"), 1)
        self.assertIn("g_task_run_in_thread (task, ft5955_identify_worker)", code)
        self.assertIn("ft5955_print_template_clear (&job->templates[i])", code)
        self.assertIn("g_cancellable_set_error_if_cancelled", code)
        self.assertIn('fpi_device_identify_report (dev, match, NULL, NULL)', code)
        old = ('if (verdict == FT5955_IDENTIFY_RETRY)\n'
               '            {\n'
               '              retry = TRUE;\n'
               '              break;')
        self.assertIn(old, before)
        self.assertNotIn(old, code)
        retry = code.split("if (verdict == FT5955_IDENTIFY_RETRY)", 1)[1].split(
            "if (verdict == FT5955_IDENTIFY_MATCH)", 1
        )[0]
        self.assertIn("retry = TRUE;", retry)
        self.assertIn("continue;", retry)
        self.assertNotIn("break;", retry)
        self.assertIn("if (decided || !retry)", code)
        self.assertIn("if (!decided)", code)
        self.assertEqual(code.count('FT5955TIMING phase=%s'), 1)

    def test_event_only_trace_and_separate_stage_contract(self):
        self.apply_v1()
        apply_identify_v2_variant(self.source)
        code = (self.source / ACTION).read_text()
        phases = (
            "identify_gateway_start", "identify_gateway_ready",
            "identify_matcher_reply", "identify_gateway_cleanup_begin",
            "identify_gateway_cleanup_done", "identify_worker_start",
            "identify_scan_begin", "identify_image_captured",
            "identify_quality_retry", "identify_match",
            "identify_gallery_no_match", "identify_worker_end",
            "identify_finish_start", "identify_finish_done",
        )
        for phase in phases:
            self.assertEqual(code.count(f'ft5955_trace ("{phase}");'), 1, phase)
        self.assertNotIn("FT5955TIMING template", code)
        self.assertNotIn("FT5955TIMING frame", code)
        # Historical snapshot is SHA-pinned and must remain immutable.
        for relative, digest in self.snap_hashes.items():
            self.assertEqual(hashlib.sha256((SNAP / relative).read_bytes()).hexdigest(),
                             digest, relative)

    def test_fail_before_change_if_v1_is_absent_or_source_moved(self):
        # Untransformed source must be rejected; no writes to action C.
        p = self.source / ACTION
        before = p.read_bytes()
        with self.assertRaisesRegex(ValueError, "requires the existing timingtrace"):
            apply_identify_v2_variant(self.source)
        self.assertEqual(before, p.read_bytes())

        self.apply_v1()
        p.write_text(p.read_text().replace(
            "              break;  /* rejected image: require a fresh touch */",
            "              continue; /* unexpected older source */",
            1))
        current = p.read_bytes()
        with self.assertRaisesRegex(ValueError, "Unexpected identify v2 source anchor"):
            apply_identify_v2_variant(self.source)
        self.assertEqual(current, p.read_bytes())

    def test_refuse_double_application(self):
        self.apply_v1()
        apply_identify_v2_variant(self.source)
        before = (self.source / ACTION).read_bytes()
        with self.assertRaisesRegex(ValueError, "Unexpected identify v2 source anchor"):
            apply_identify_v2_variant(self.source)
        self.assertEqual(before, (self.source / ACTION).read_bytes())


if __name__ == "__main__":
    unittest.main()
