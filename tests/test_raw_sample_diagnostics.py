"""Synthetic-only tests: no fingerprint images, no USB, no network."""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from raw_sample_diagnostics import summarise, read_private, recent_four
from raw_to_png import RAW_BYTES


class RawSampleDiagnosticsTests(unittest.TestCase):
    def test_signed_negative_detection(self):
        values = (0, 100, 32767, 32768, 65535) * 1024
        m = summarise(values)
        self.assertEqual(m["negative_pct"], 40)
        self.assertEqual(m["zero_after_clamp_pct"], 60)
        self.assertEqual(m["positive_distinct"], 2)

    def test_all_positive(self):
        m = summarise((1000,) * (RAW_BYTES // 2))
        self.assertEqual(m["negative_pct"], 0)
        self.assertEqual(m["zero_after_clamp_pct"], 0)
        self.assertEqual(m["unsigned_p50"], 1000)

    def test_bad_sample_length(self):
        with self.assertRaises(ValueError):
            summarise((0, 1, 2))

    def test_bad_file_size(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "test.raw"
            path.write_bytes(b"xx")
            with self.assertRaises(ValueError):
                read_private(path)

    def test_regular_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "test.raw"
            fake = bytes(RAW_BYTES)
            path.write_bytes(fake)
            self.assertEqual(read_private(path), fake)

    def test_four_labels(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            for label in ("A1", "A2", "B1", "B2"):
                (folder / f"fingerprint_11-10-2026_14-24-00_{label}.raw").write_bytes(b"fake")
            self.assertEqual(
                [p.name.rsplit("_", 1)[-1] for p in recent_four(folder)],
                ["A1.raw", "A2.raw", "B1.raw", "B2.raw"],
            )

    def test_symlink_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            real = Path(tmp) / "real.raw"
            real.write_bytes(bytes(RAW_BYTES))
            link = Path(tmp) / "link.raw"
            link.symlink_to(real)
            with self.assertRaises(ValueError):
                read_private(link)


if __name__ == "__main__":
    unittest.main()
