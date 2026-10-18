"""Offline assertions for the FT5955 experimental early-contact staging variant.

This does NOT run the fingerprint driver, access hardware, enrol, or match.
"""
from pathlib import Path
import hashlib
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from verify_ft5955_clean_clone import (
    ACTION_SOURCE, CAPTURE_SOURCE, apply_earlycapture_variant, apply_poll100_variant,
)

BASE = ROOT / "driver" / "live-snapshot-2026-10-16"


class EarlyCaptureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.source = Path(self.tmp.name)
        self.hashes = {}
        for rel in (ACTION_SOURCE, CAPTURE_SOURCE):
            original = BASE / rel
            target = self.source / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            data = original.read_bytes()
            target.write_bytes(data)
            self.hashes[rel] = hashlib.sha256(data).hexdigest()

    def test_verify_starts_capture_during_gateway_startup(self):
        apply_poll100_variant(self.source)
        apply_earlycapture_variant(self.source)
        action = (self.source / ACTION_SOURCE).read_text()
        capture = (self.source / CAPTURE_SOURCE).read_text()
        self.assertIn('init_thread=g_thread_new("ft5955-gateway-start"', action)
        self.assertIn("if(job->enrolling) {", action)
        self.assertIn("if(!ft5955_native_scan(job->usb,c,frame,&err))goto end;", action)
        self.assertIn("g_thread_join(init_thread);", action)
        self.assertIn("g_cancellable_cancel(init.cancel);", action)
        self.assertIn("if(!init.ready)", action)
        self.assertIn("g_clear_object(&init.cancel)", action)
        self.assertIn('write_all(out,"FRAME\\n",6,c,&err)', action)
        # In verify worker, USB acquisition happens before waiting for READY.
        worker = action[action.index("static void worker ("):]
        self.assertLess(worker.index("ft5955_native_scan("),
                        worker.index("g_thread_join(init_thread);"))
        self.assertLess(worker.index("g_thread_join(init_thread);"),
                        worker.index('write_all(out,"FRAME\\n"'))
        self.assertIn("gint64 pause=100000-", capture)
        self.assertIn("for(unsigned poll=0;poll<1200;poll++)", capture)
        self.assertIn("if(touch==6)armed=TRUE;", capture)
        self.assertIn("if(armed && touch==5)", capture)
        self.assertIn("g_usleep(10000);", capture)
        # Proven snapshot is never modified by the disposable transforms.
        for rel, digest in self.hashes.items():
            self.assertEqual(hashlib.sha256((BASE / rel).read_bytes()).hexdigest(), digest)

    def test_rejects_modified_action_source(self):
        target = self.source / ACTION_SOURCE
        data = target.read_text().replace(
            "  if(!start_gateway(job,&child,&in,&out,c,&err) || !startup(job,in,out,c,&err))goto end;",
            "  /* no longer an expected startup anchor */", 1)
        target.write_text(data)
        with self.assertRaisesRegex(ValueError, "Unexpected native action anchor"):
            apply_earlycapture_variant(self.source)

    def test_refuses_repeat_or_symlink(self):
        apply_earlycapture_variant(self.source)
        with self.assertRaisesRegex(ValueError, "Unexpected native action anchor"):
            apply_earlycapture_variant(self.source)
        action = self.source / ACTION_SOURCE
        action.unlink()
        action.symlink_to(BASE / ACTION_SOURCE)
        with self.assertRaisesRegex(ValueError, "Missing regular"):
            apply_earlycapture_variant(self.source)


if __name__ == "__main__":
    unittest.main()
