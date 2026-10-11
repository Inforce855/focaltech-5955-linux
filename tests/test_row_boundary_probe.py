"""Pure synthetic tests for 64/80 candidate row-boundary probe."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from row_boundary_probe import seam_statistics, quantile


def synthetic_smooth_rows(width: int) -> tuple[int, ...]:
    """5120 samples; within-row difference ~1, end-of-row wrap is large."""
    height = 5120 // width
    return tuple(1000 + y * 2 + x for y in range(height) for x in range(width))


class RowBoundaryTests(unittest.TestCase):
    def test_expected_seams(self):
        data = synthetic_smooth_rows(64)
        a = seam_statistics(data, 64)
        self.assertEqual(a["seams"], 79)
        self.assertEqual(a["rows"], 80)
        b = seam_statistics(data, 80)
        self.assertEqual(b["seams"], 63)
        self.assertEqual(b["rows"], 64)

    def test_64_width_selected_by_discontinuities(self):
        data = synthetic_smooth_rows(64)
        a, b = seam_statistics(data, 64), seam_statistics(data, 80)
        self.assertGreater(a["seam_over_within"], 10.0)
        self.assertGreater(a["seam_over_within"], b["seam_over_within"])
        self.assertGreater(a["seams_over_p90_pct"], b["seams_over_p90_pct"])

    def test_80_width_selected_by_discontinuities(self):
        data = synthetic_smooth_rows(80)
        a, b = seam_statistics(data, 80), seam_statistics(data, 64)
        self.assertGreater(a["seam_over_within"], 10.0)
        self.assertGreater(a["seam_over_within"], b["seam_over_within"])
        self.assertGreater(a["seams_over_p90_pct"], b["seams_over_p90_pct"])

    def test_constant_image_does_not_choose_a_width(self):
        data = (1000,) * 5120
        a, b = seam_statistics(data, 64), seam_statistics(data, 80)
        self.assertEqual(a["seam_median"], 0)
        self.assertEqual(b["seam_median"], 0)
        self.assertEqual(a["seam_over_within"], 1)
        self.assertEqual(b["seam_over_within"], 1)

    def test_error_handling(self):
        with self.assertRaises(ValueError):
            seam_statistics((1, 2), 64)
        with self.assertRaises(ValueError):
            seam_statistics(synthetic_smooth_rows(64), 16)
        with self.assertRaises(ValueError):
            quantile([], 0.5)


if __name__ == "__main__":
    unittest.main()
