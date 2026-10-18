"""Offline FT5955 timing-only diagnostics regression (zero USB, no fingerprints)."""
from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from verify_ft5955_clean_clone import (
    ACTION_SOURCE, CAPTURE_SOURCE, apply_earlycapture_variant,
    apply_poll100_variant, apply_timingtrace_variant
)

SNAP = ROOT / "driver" / "live-snapshot-2026-10-16"
PHASES = (
    "worker_start", "gateway_ready", "scan_begin",
    "first_status_present", "first_status_absent",
    "contact_off_observed", "contact_on_observed", "image_captured",
    "matcher_reply_received", "matcher_quality_retry",
    "matcher_match", "matcher_no_match", "cleanup_begin",
    "gateway_wait_complete", "worker_return", "verify_finish_start",
    "verify_finish_done"
)


class TimingTraceTests(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.root = Path(self.t.name)
        self.hashes = {}
        for rel in (ACTION_SOURCE, CAPTURE_SOURCE):
            p = self.root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            raw = (SNAP / rel).read_bytes()
            p.write_bytes(raw)
            self.hashes[rel] = hashlib.sha256(raw).hexdigest()

    def test_instrument_existing_parallel_variant_without_protocol_change(self):
        apply_poll100_variant(self.root)
        apply_earlycapture_variant(self.root)
        original_action = (self.root / ACTION_SOURCE).read_text()
        original_capture = (self.root / CAPTURE_SOURCE).read_text()
        apply_timingtrace_variant(self.root)
        action = (self.root / ACTION_SOURCE).read_text()
        capture = (self.root / CAPTURE_SOURCE).read_text()
        for phase in PHASES:
            self.assertIn('"' + phase + '"', action + capture)
        for source in (action, capture):
            self.assertEqual(source.count('FT5955TIMING phase='), 1)
            self.assertIn('g_get_monotonic_time ()', source)
            self.assertNotIn('FT5955TIMING raw', source)
            self.assertNotIn('FT5955TIMING template', source)
        self.assertIn('g_message ("FT5955TIMING phase=%s mono_us=%" G_GINT64_FORMAT,', action)
        self.assertIn('ft5955_trace ("gateway_ready");', action)
        self.assertIn('ft5955_trace ("image_captured");', action)
        self.assertIn('ft5955_trace ("matcher_reply_received");', action)
        self.assertIn('ft5955_trace ("gateway_wait_complete");', action)
        self.assertIn('ft5955_trace ("verify_finish_done");', action)
        self.assertIn('g_thread_join(init_thread);', action)
        self.assertIn('if(job->enrolling) {', action)
        self.assertIn('g_cancellable_cancel(c)', action)
        self.assertIn('g_usleep(10000);', capture)
        self.assertIn('for(unsigned poll=0;poll<1200;poll++)', capture)
        self.assertIn('if(armed && touch==5)', capture)
        # All source-level USB status, ready and image commands unchanged
        for command in ('status_cmd[]=', 'ready_cmd[]=', 'image_cmd[]='):
            self.assertEqual(capture.split(command)[1].split(';', 1)[0],
                             original_capture.split(command)[1].split(';', 1)[0])
        self.assertEqual(action.count('write_all(out,"FRAME\\n",6,c,&err)'),
                         original_action.count('write_all(out,"FRAME\\n",6,c,&err)'))
        self.assertLess(action.index('ft5955_trace ("matcher_match")') if
                        'ft5955_trace ("matcher_match")' in action else
                        action.index('ft5955_trace (job->pending'), action.index('ft5955_trace ("cleanup_begin")'))
        self.assertLess(action.index('ft5955_trace ("gateway_wait_complete")'),
                        action.index('ft5955_trace ("worker_return")'))
        self.assertLess(action.index('ft5955_trace ("verify_finish_start")'),
                        action.index('ft5955_trace ("verify_finish_done")'))
        for rel, digest in self.hashes.items():
            self.assertEqual(hashlib.sha256((SNAP / rel).read_bytes()).hexdigest(), digest)

    def test_requires_parallel_variant_and_fail_closed(self):
        with self.assertRaisesRegex(ValueError, 'Unexpected timing-instrumentation anchor'):
            apply_timingtrace_variant(self.root)
        # Neither source changed if transformation preflight fails
        for rel, digest in self.hashes.items():
            self.assertEqual(hashlib.sha256((self.root / rel).read_bytes()).hexdigest(), digest)

    def test_refuses_repeat_and_symlink(self):
        apply_poll100_variant(self.root)
        apply_earlycapture_variant(self.root)
        apply_timingtrace_variant(self.root)
        with self.assertRaisesRegex(ValueError, 'Unexpected timing-instrumentation anchor'):
            apply_timingtrace_variant(self.root)
        path = self.root / ACTION_SOURCE
        path.unlink()
        path.symlink_to(SNAP / ACTION_SOURCE)
        with self.assertRaisesRegex(ValueError, 'Missing regular'):
            apply_timingtrace_variant(self.root)


if __name__ == "__main__":
    unittest.main()
