"""Synthetic-only tests for the cross-session private capture diagnostic."""
from __future__ import annotations

from contextlib import redirect_stdout
import io
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))
from cross_session_eval import (  # noqa: E402
    is_same_physical_finger, score_sessions, session_files, summarize,
)


class SessionTests(unittest.TestCase):
    def test_role_reversal_truth_table(self):
        genuine_swapped = {(i, j) for i in range(4) for j in range(4)
                           if is_same_physical_finger(i, j, swapped=True)}
        self.assertEqual(len(genuine_swapped), 8)
        self.assertIn((0, 2), genuine_swapped)
        self.assertIn((3, 1), genuine_swapped)
        self.assertNotIn((0, 0), genuine_swapped)
        genuine_unswapped = {(i, j) for i in range(4) for j in range(4)
                             if is_same_physical_finger(i, j, swapped=False)}
        self.assertEqual(len(genuine_unswapped), 8)
        self.assertIn((0, 0), genuine_unswapped)
        self.assertNotIn((0, 2), genuine_unswapped)

    def test_find_four_labelled_files_not_by_mtime(self):
        with TemporaryDirectory() as tmp:
            folder = Path(tmp)
            names = [
                "fingerprint_11-10-2026_14-24-20_A1.raw",
                "fingerprint_11-10-2026_14-24-24_A2.raw",
                "fingerprint_11-10-2026_14-24-37_B1.raw",
                "fingerprint_11-10-2026_14-24-42_B2.raw",
            ]
            for name in reversed(names):
                (folder / name).write_bytes(b"x")
            selection = session_files(folder, "11-10-2026_14-24")
            self.assertEqual([p.name for p in selection], names)

    def test_missing_duplicate_or_symlinked_sessions_are_rejected(self):
        with TemporaryDirectory() as tmp:
            folder = Path(tmp)
            for i, label in enumerate(("A1", "A2", "B1", "B2")):
                (folder / f"fingerprint_11-10-2026_14-55-{i:02d}_{label}.raw").write_bytes(b"x")
            self.assertEqual(len(session_files(folder, "11-10-2026_14-55")), 4)
            (folder / "fingerprint_11-10-2026_14-55-59_A1.raw").write_bytes(b"x")
            with self.assertRaises(ValueError):
                session_files(folder, "11-10-2026_14-55")
            with self.assertRaises(ValueError):
                session_files(folder, "../not-a-valid-prefix")

    def test_all_sixteen_pairings_are_scored(self):
        early = [bytes([i]) * 5120 for i in range(4)]
        late = [bytes([i + 4]) * 5120 for i in range(4)]
        fake = SimpleNamespace(correlation=0.25, dx=0, dy=0)
        with (patch("cross_session_eval.preprocess_samples", side_effect=lambda x, **kwargs: x),
              patch("cross_session_eval.compare", return_value=fake)):
            rows = score_sessions(early, late, width=64, height=80, swapped=True)
        self.assertEqual(len(rows), 16)
        self.assertEqual(sum(1 for row in rows if row[2]), 8)
        self.assertEqual(sum(1 for row in rows if not row[2]), 8)

    def test_summarize_reports_no_false_success(self):
        records = []
        for i in range(4):
            for j in range(4):
                same = is_same_physical_finger(i, j, swapped=True)
                records.append((i, j, same, 0.2 if same else 0.4, 6, 0))
        stream = io.StringIO()
        with redirect_stdout(stream):
            summarize(records)
        self.assertIn("Genuine pairs beating EVERY different-finger control: 0/8",
                      stream.getvalue())
        self.assertIn("Strict separation", stream.getvalue())
        self.assertIn("16/16", stream.getvalue())


if __name__ == "__main__":
    unittest.main()
