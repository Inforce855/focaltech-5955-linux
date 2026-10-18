#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Synthetic, no-root, no-biometrics tests for the MOH path audit."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

source = Path(__file__).resolve().parents[1] / "tools" / "audit_ft5955_auth_paths.py"
spec = importlib.util.spec_from_file_location("audit_ft5955_auth_paths", source)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class AuditTests(unittest.TestCase):
    def test_relative_path_rejected(self):
        self.assertTrue(mod.audit_path(Path("relative.py")))

    def test_missing_file_rejected(self):
        self.assertTrue(mod.audit_path(Path("/definitely-absent-ft5955-file")))

    def test_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "target"
            target.write_text("test")
            link = Path(directory) / "link"
            link.symlink_to(target)
            self.assertTrue(any("symlink" in s for s in mod.audit_path(link, expected_uid=0)))

    def test_user_owned_path_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            filename = Path(directory) / "gateway.py"
            filename.write_text("test")
            if filename.stat().st_uid != 0:
                self.assertTrue(any("owner uid" in s for s in mod.audit_path(filename)))


if __name__ == "__main__":
    unittest.main()
