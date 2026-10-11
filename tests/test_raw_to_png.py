"""Offline conversion tests; no biometric data or hardware access."""
import struct
import sys
import tempfile
from pathlib import Path
import unittest
import zlib

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from raw_to_png import (
    PIXELS, RAW_BYTES, SIGNATURE, decode_samples, greyscale_png,
    save_private, to_8bit, upscale_nn,
)


class ImageConversionTests(unittest.TestCase):
    def test_decode_endian(self):
        sequence = tuple((i * 257) & 65535 for i in range(PIXELS))
        self.assertEqual(decode_samples(struct.pack(">" + f"{PIXELS}H", *sequence), "big"), sequence)
        self.assertEqual(decode_samples(struct.pack("<" + f"{PIXELS}H", *sequence), "little"), sequence)

    def test_wrong_raw_size(self):
        with self.assertRaises(ValueError):
            decode_samples(bytes(RAW_BYTES - 1), "big")

    def test_flat_frame_is_black(self):
        self.assertEqual(to_8bit((1000,) * PIXELS), bytes(PIXELS))

    def test_gradient_stretch(self):
        gradient = tuple(range(PIXELS))
        result = to_8bit(gradient)
        self.assertEqual(len(result), PIXELS)
        self.assertGreater(max(result), min(result))

    def test_16bit_png_roundtrip(self):
        raw = struct.pack(">8H", *range(8))
        png = greyscale_png(raw, 4, 2, bits=16)
        self.assertTrue(png.startswith(SIGNATURE))
        width, height, depth, colour = struct.unpack(">IIBB", png[16:26])
        self.assertEqual((width, height, depth, colour), (4, 2, 16, 0))
        length = struct.unpack(">I", png[33:37])[0]
        data = zlib.decompress(png[41:41 + length])
        self.assertEqual(data, b"\x00" + raw[:8] + b"\x00" + raw[8:])

    def test_upscale(self):
        pixels = bytes([2, 4, 6, 8])
        self.assertEqual(upscale_nn(pixels, 2, 2, 2), bytes([2, 2, 4, 4] * 2 + [6, 6, 8, 8] * 2))

    def test_private_file_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "local-data" / "test.png"
            save_private(p, b"xyz")
            self.assertEqual(p.stat().st_mode & 0o777, 0o600)
            with self.assertRaises(FileExistsError):
                save_private(p, b"abc")


if __name__ == "__main__":
    unittest.main()
