#!/usr/bin/env python3
"""No biometric data, no USB, no native libfprint required."""
from pathlib import Path
import unittest

root = Path(__file__).resolve().parent.parent
source = (root / "tests" / "native_print_roundtrip.c").read_text()
build = (root / "build_private_test.sh").read_text()

class ValidateStatic(unittest.TestCase):
    def test_context_reset(self):
        for item in (
            'fp_print_serialize(', 'fp_print_deserialize(',
            'g_clear_object(&enrolled);', 'g_clear_object(&context);',
            'context = fp_context_new();', 'fp_device_verify_sync(',
            '"DIFFERENT finger (B, control 1)"',
            '"ENROLLED finger (A, control 6)"',
        ):
            self.assertIn(item, source)
        self.assertGreaterEqual(source.count('context = fp_context_new();'), 2)
        self.assertEqual(source.count('TRUE},'), 6)
        self.assertEqual(source.count('FALSE},'), 4)
    def test_private_only(self):
        self.assertIn('-Wl,-rpath,', build)
        self.assertIn('ldd build-tests/native_print_roundtrip', build)
        self.assertIn('geteuid() == 0', source)
        self.assertIn('FT5955_EXPERIMENTAL_ENABLE', source)
    def test_diagnostic_accounts_for_failures(self):
        for item in (
            'fp_device_retry_quark()', 'on_verify_report',
            'same_count - same_match', 'different_count - different_no_match',
            'if (match != trials[i].expected) unexpected++;',
            'incomplete diagnostic, not PASS', 'ret = 8;'
        ):
            self.assertIn(item, source)

    def test_no_disk_serialize(self):
        self.assertNotIn('fopen(', source)
        self.assertNotIn('fwrite(', source)
        self.assertNotIn('g_file_set_contents(', source)

if __name__ == '__main__':
    unittest.main(verbosity=2)
