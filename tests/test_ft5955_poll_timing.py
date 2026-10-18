"""Offline-only timing variant regression tests; no fprintd, MOH or sensor."""
from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from verify_ft5955_clean_clone import apply_poll100_variant, CAPTURE_SOURCE

BASELINE = ROOT / "driver" / "live-snapshot-2026-10-16" / CAPTURE_SOURCE


class PollingTimingTests(unittest.TestCase):
    def _copy(self, root: Path) -> Path:
        out = root / CAPTURE_SOURCE
        out.parent.mkdir(parents=True)
        out.write_bytes(BASELINE.read_bytes())
        return out

    def test_timing_only_with_bounded_duration(self):
        before = BASELINE.read_bytes()
        digest = hashlib.sha256(before).hexdigest()
        with tempfile.TemporaryDirectory() as tmp:
            target = self._copy(Path(tmp))
            apply_poll100_variant(Path(tmp))
            new = target.read_text(encoding="utf-8")
            original = before.decode("utf-8")
            self.assertIn("for(unsigned poll=0;poll<1200;poll++)", new)
            self.assertIn("gint64 pause=100000-(g_get_monotonic_time()-started)", new)
            self.assertIn("g_usleep(10000)", new)
            self.assertIn("if(touch==6)armed=TRUE", new)
            self.assertIn("if(armed && touch==5)", new)
            self.assertEqual(new.count("status_cmd"), original.count("status_cmd"))
            self.assertEqual(new.count("ready_cmd"), original.count("ready_cmd"))
            self.assertEqual(new.count("image_cmd"), original.count("image_cmd"))
            expected = (original.replace(" * 240 polls (two minutes)",
                                         " * 1200 polls (two minutes)")
                        .replace("for(unsigned poll=0;poll<240;poll++) {",
                                 "for(unsigned poll=0;poll<1200;poll++) {")
                        .replace("gint64 pause=500000-(g_get_monotonic_time()-started);",
                                 "gint64 pause=100000-(g_get_monotonic_time()-started);")
                        .replace("No fresh FT5955 touch within 240 status checks",
                                 "No fresh FT5955 touch within 1200 status checks"))
            self.assertEqual(new, expected)
        self.assertEqual(hashlib.sha256(BASELINE.read_bytes()).hexdigest(), digest)

    def test_fails_closed_on_unexpected_capture_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = self._copy(Path(tmp))
            before = target.read_bytes().replace(b"g_usleep(10000);",
                                                  b"g_usleep(15000);")
            target.write_bytes(before)
            with self.assertRaisesRegex(ValueError, "10ms"):
                apply_poll100_variant(Path(tmp))
            # It may already have written a temporary copy, but never touches
            # the immutable snapshot. Disposable build is removed on failure.
        self.assertIn(b"g_usleep(10000);", BASELINE.read_bytes())


if __name__ == "__main__":
    unittest.main()
