#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Offline guard checks; never invoke --install or use root."""
import ast
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/manage_ft5955_moh_dev.sh"
MOCK = ROOT / "tools/ft5955_dev_mock_server.py"

class DevInstallationGuards(unittest.TestCase):
    def test_shell_syntax(self):
        subprocess.run(["bash", "-n", str(SCRIPT)], check=True)

    def test_mock_syntax(self):
        ast.parse(MOCK.read_text())

    def test_script_only_touches_dev_units(self):
        content = SCRIPT.read_text()
        self.assertIn("ft5955-engine-dev.socket", content)
        self.assertIn("ft5955-engine-dev.service", content)
        self.assertIn("assert_live", content)
        self.assertIn("installation marker missing", content)
        self.assertNotIn("systemctl restart fprintd", content)
        self.assertNotIn("authselect enable-feature", content)

    def test_guarded_usage(self):
        completed = subprocess.run(["bash", str(SCRIPT), "--unsupported"],
                                   capture_output=True, text=True)
        self.assertEqual(completed.returncode, 2)

if __name__ == "__main__":
    unittest.main()
