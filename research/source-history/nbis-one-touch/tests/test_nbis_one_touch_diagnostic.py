"""No biometric material or sensor access: test the diagnostic's orchestration."""
from __future__ import annotations

import io
from pathlib import Path
import sys
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

TOOLS = Path(__file__).resolve().parents[1] / 'tools'
sys.path.insert(0, str(TOOLS))
# The existing bridge lives in the repo and is imported by the diagnostic.
import nbis_one_touch_diagnostic as diag


class TestNbisDiagnostic(unittest.TestCase):
    def test_inversion_lut(self):
        self.assertEqual(b'\x00\x7f\xff'.translate(diag.INVERT_TABLE), b'\xff\x80\x00')

    def test_scan_runs_both_polarities_and_two_methods(self):
        fake = b'\x30' * (diag.WIDTH * diag.HEIGHT)
        recorded = []
        def test_probe(data, w, h):
            recorded.append((len(data), w, h, data[0]))
            return 1
        with patch.object(diag, 'normalize', return_value=fake), \
             patch.object(diag, 'probe_minutiae', side_effect=test_probe), \
             redirect_stdout(io.StringIO()):
            out = diag.diagnose(b'\x00' * diag.RAW_BYTES, scales=(1, 2))
        self.assertEqual(len(out), 8)
        self.assertEqual({(w, h) for _, w, h, _ in recorded}, {(64, 80), (128, 160)})
        self.assertEqual({pix for _, _, _, pix in recorded}, {48, 207})


if __name__ == '__main__':
    unittest.main()
