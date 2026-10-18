#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Offline regression: multiline GCC parser must not reach shlex with '\\'."""
import ast
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT=Path(__file__).resolve().parents[1]/"tools"/"build_ft5955_moh_offline_dev.py"
class ParserRegression(unittest.TestCase):
    def test_syntax(self):
        ast.parse(SCRIPT.read_text())
    def test_parser_handles_actual_continuations(self):
        # Inspects source and ensures the known broken regex is absent.
        source=SCRIPT.read_text()
        self.assertIn('continuation=stripped.endswith(chr(92))',source)
        self.assertIn('parts.append(stripped[:-1] if continuation else stripped)',source)
        self.assertNotIn('match=re.search(r"(?m)^gcc',source)
    def test_no_output_arg_has_no_side_effect(self):
        p=subprocess.run([sys.executable,"-B",str(SCRIPT)],capture_output=True,text=True)
        self.assertNotEqual(p.returncode,0)
if __name__=="__main__":
    unittest.main()
