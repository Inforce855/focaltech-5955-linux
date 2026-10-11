"""Synthetic-only tests for offline signed little-endian FocalTech previews."""
from pathlib import Path
import stat
import struct
import sys
from tempfile import TemporaryDirectory
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from raw_decode_preview import (
    SAMPLE_COUNT, preview_png, private_directory, read_capture,
    remove_row_offsets, signed_clamp, stretch_foreground,
)
from raw_to_png import RAW_BYTES


class RawDecodePreviewTests(unittest.TestCase):
    def test_signed_clamp(self):
        values = (0, 1200, 32767, 32768, 65535) * 1024
        converted = signed_clamp(values)
        self.assertEqual(converted[:5], [0, 1200, 32767, 0, 0])

    def test_signed_clamp_wrong_count(self):
        with self.assertRaises(ValueError):
            signed_clamp((1, 2, 3))

    def test_row_normalisation_reduces_offset(self):
        width, height = 64, 80
        # Entirely synthetic, with per-row additive stripe offsets.
        pixels = [1000 + 10 * y + (x % 17) * 3
                  for y in range(height) for x in range(width)]
        output = remove_row_offsets(pixels, width, height)
        first_medians = [sorted(pixels[y * width:(y + 1) * width])[width // 2]
                         for y in range(height)]
        last_medians = [sorted(output[y * width:(y + 1) * width])[width // 2]
                        for y in range(height)]
        self.assertGreater(max(first_medians) - min(first_medians), 700)
        self.assertLessEqual(max(last_medians) - min(last_medians), 2)

    def test_zero_background_is_preserved(self):
        width, height = 80, 64
        pixels = [0 if x < 10 else (1000 + 2 * y + x % 7)
                  for y in range(height) for x in range(width)]
        fixed = remove_row_offsets(pixels, width, height)
        for y in range(height):
            self.assertEqual(fixed[y * width:y * width + 10], [0] * 10)

    def test_synthetic_64x80_png(self):
        pixels = [1000 + (x + y) % 200 for y in range(80) for x in range(64)]
        png = preview_png(pixels, 64, 80, 8)
        self.assertEqual(png[:8], b"\x89PNG\r\n\x1a\n")
        self.assertEqual(struct.unpack(">II", png[16:24]), (512, 640))

    def test_synthetic_80x64_png(self):
        pixels = [1000 + (x + y) % 100 for y in range(64) for x in range(80)]
        png = preview_png(pixels, 80, 64, 8)
        self.assertEqual(struct.unpack(">II", png[16:24]), (640, 512))

    def test_all_zero_display_is_zero(self):
        self.assertEqual(stretch_foreground([0] * SAMPLE_COUNT),
                         bytes(SAMPLE_COUNT))

    def test_invalid_layout_size_is_rejected(self):
        with self.assertRaises(ValueError):
            remove_row_offsets([100] * 100, 80, 64)

    def test_private_output_dir(self):
        with TemporaryDirectory() as tmp:
            output = private_directory(Path(tmp) / "private")
            self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o700)

    def test_invalid_raw_size(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.raw"
            path.write_bytes(b"abc")
            with self.assertRaises(ValueError):
                read_capture(path)

    def test_symlinked_raw_refused(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "private.raw"
            path.write_bytes(bytes(RAW_BYTES))
            link = Path(tmp) / "alias.raw"
            link.symlink_to(path)
            with self.assertRaises(ValueError):
                read_capture(link)


if __name__ == "__main__":
    unittest.main()
