"""Offline tests using synthetic data only; no biometric images."""
from pathlib import Path
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from sift_compare import (
    LAYOUTS, PAIRS, dependencies, enhance, extract_features, safe_raw, score_pair
)
from raw_to_png import RAW_BYTES


class SiftComparisonTests(unittest.TestCase):
    def test_layouts(self):
        self.assertEqual(LAYOUTS["64x80"], (64, 80))
        self.assertEqual(LAYOUTS["80x64"], (80, 64))
        self.assertEqual(len(PAIRS), 6)

    def test_reject_truncated_raw(self):
        with tempfile.TemporaryDirectory() as directory:
            raw = Path(directory) / "test.raw"
            raw.write_bytes(b"abc")
            with self.assertRaises(ValueError):
                safe_raw(raw)

    def test_reject_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            raw = Path(directory) / "capture.raw"
            raw.write_bytes(bytes(RAW_BYTES))
            link = Path(directory) / "link.raw"
            link.symlink_to(raw)
            with self.assertRaises(ValueError):
                safe_raw(link)

    def test_read_synthetic_raw(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.raw"
            data = bytes(RAW_BYTES)
            path.write_bytes(data)
            self.assertEqual(safe_raw(path), data)

    def test_synthetic_wrong_geometry(self):
        np, cv2 = dependencies()
        with self.assertRaises(ValueError):
            enhance(bytes(RAW_BYTES), 100, 51, np, cv2)

    def test_preprocess_black_and_output_shape(self):
        np, cv2 = dependencies()
        pixels = bytes(RAW_BYTES)
        for width, height in LAYOUTS.values():
            processed = enhance(pixels, width, height, np, cv2)
            self.assertEqual(processed.shape, (height * 10, width * 10))
            self.assertEqual(processed.dtype, np.uint8)

    def test_match_missing_descriptors(self):
        np, cv2 = dependencies()
        self.assertEqual(score_pair(([], None), ([], None), np, cv2), (0, 0))

    def test_synthetic_self_match(self):
        np, cv2 = dependencies()
        # Synthetic checkerboard plus circular blobs: not a real fingerprint.
        shape = (800, 640)
        img = np.zeros(shape, dtype=np.uint8)
        for y in range(30, 770, 70):
            for x in range(30, 610, 70):
                shade = 255 if (x + y) % 3 else 130
                cv2.circle(img, (x, y), 12, shade, -1)
        cv2.putText(img, "TEST", (110, 310), cv2.FONT_HERSHEY_SIMPLEX, 2, 255, 5)
        features = extract_features(img, cv2)
        self.assertGreater(len(features[0]), 5)
        good, inliers = score_pair(features, features, np, cv2)
        self.assertGreater(good, 0)
        self.assertGreater(inliers, 0)


if __name__ == "__main__":
    try:
        dependencies()
    except RuntimeError:
        print("OpenCV unavailable; install the optional dependency to run SIFT tests.")
    unittest.main()
