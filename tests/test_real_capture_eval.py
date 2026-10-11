"""Synthetic-only tests of local real-capture diagnostic plumbing.

No actual biometrics, USB, vendor binaries or network access.
"""
from __future__ import annotations

import pathlib
import sys
import tempfile
import unittest

TOOLS = pathlib.Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))
from real_capture_eval import (  # noqa: E402
    EXECUTABLE, contact_sheet, convert_using_native, read_private_capture,
)


class RealCaptureBridgeTests(unittest.TestCase):
    def test_contact_sheet_png_is_correct_size(self):
        """Four quadrants are combined without loss of their pixel ordering."""
        import struct
        import zlib

        width, height, zoom = 64, 80, 2
        images = [bytes([c]) * (width * height) for c in (10, 20, 30, 40)]
        png = contact_sheet(images, width, height, zoom)
        self.assertEqual(png[:8], b"\x89PNG\r\n\x1a\n")
        w, h = struct.unpack(">II", png[16:24])
        self.assertEqual((w, h), (256, 320))
        # Read just the one IDAT chunk produced by our existing PNG writer.
        at = 8
        compressed = None
        while at < len(png):
            count = struct.unpack(">I", png[at:at+4])[0]
            name = png[at+4:at+8]
            payload = png[at+8:at+8+count]
            at += 12 + count
            if name == b"IDAT":
                compressed = payload
        self.assertIsNotNone(compressed)
        decompressed = zlib.decompress(compressed)
        row_length = 1 + w
        self.assertEqual(decompressed[1], 10)
        self.assertEqual(decompressed[1 + 130], 20)
        self.assertEqual(decompressed[(height * zoom) * row_length + 1], 30)
        self.assertEqual(decompressed[(height * zoom) * row_length + 1 + 130], 40)

    def test_rejects_wrong_size_and_symlink(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            raw = root / "synthetic.raw"
            raw.write_bytes(b"\0" * 100)
            with self.assertRaises(ValueError):
                read_private_capture(raw)
            link = root / "linked.raw"
            link.symlink_to(raw)
            with self.assertRaises(ValueError):
                read_private_capture(link)
            with self.assertRaises(ValueError):
                convert_using_native(b"\0" * 8)

    @unittest.skipUnless(EXECUTABLE.is_file(), "native CLI not built yet")
    def test_native_subprocess_on_synthetic_gradient(self):
        raw = b"".join(
            (i % 1024).to_bytes(2, "little") for i in range(5120)
        )
        result = convert_using_native(raw)
        self.assertEqual(len(result), 5120)
        self.assertEqual(result[0], 254)
        self.assertEqual(result[1023], 0)


if __name__ == "__main__":
    unittest.main()
