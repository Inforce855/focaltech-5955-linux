#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Offline tests: installation must fail closed and never touch the host."""
import subprocess
import sys
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "ft5955_moh_service_preflight.py"


class PreflightTests(unittest.TestCase):
    def test_install_is_refused(self):
        result = subprocess.run([sys.executable, "-B", str(SCRIPT), "--install"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("REFUSED", result.stdout)

    def test_no_argument_is_refused(self):
        result = subprocess.run([sys.executable, "-B", str(SCRIPT)],
                                capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)

    def test_plan_only_inspects(self):
        result = subprocess.run([sys.executable, "-B", str(SCRIPT), "--plan"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("AUTHENTICATION NOT APPROVED", result.stdout)
        self.assertIn("PAM activation remains prohibited", result.stdout)


if __name__ == "__main__":
    unittest.main()
