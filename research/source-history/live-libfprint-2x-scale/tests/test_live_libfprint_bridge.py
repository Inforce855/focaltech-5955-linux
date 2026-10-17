"""Offline-only protocol tests; synthetic bytes are NEVER actual prints."""
from __future__ import annotations
import io
import socket
import struct
import threading
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import live_libfprint_bridge as bridge


class TestLiveBridge(unittest.TestCase):
    def test_records(self):
        sample = bytes(bridge.RAW_BYTES)
        wire = b"S\x00\x02ok" + b"F" + len(sample).to_bytes(2, "big") + sample
        stream = io.BytesIO(wire)
        self.assertEqual(bridge.read_record(stream), (b"S", b"ok"))
        self.assertEqual(bridge.read_record(stream), (b"F", sample))
        self.assertIsNone(bridge.read_record(stream))

    def test_reject_invalid_record(self):
        with self.assertRaises(ValueError):
            bridge.read_record(io.BytesIO(b"F\x00\x02ab"))
        with self.assertRaises(EOFError):
            bridge.read_record(io.BytesIO(b"S\x00\x04a"))

    def test_conversion_and_socket(self):
        # Fully synthetic 64x80 sample data; no USB, identity data or uploads.
        raw = b"".join((800 + (i % 200)).to_bytes(2, "little")
                       for i in range(5120))
        processed = bridge.normalize(raw, "contrast")
        self.assertEqual(len(processed), 5120)
        enlarged = bridge.enlarge(processed)
        self.assertEqual(len(enlarged), 512000)
        a, b = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
        data = bytearray()
        def receive():
            while len(data) < 512008:
                chunk = b.recv(512008 - len(data))
                if not chunk:
                    break
                data.extend(chunk)
        reader = threading.Thread(target=receive)
        try:
            reader.start()
            bridge.send_image(a, enlarged)
            reader.join(timeout=5)
            self.assertFalse(reader.is_alive())
            self.assertEqual(len(data), 512008)
            self.assertEqual(struct.unpack("=ii", data[:8]), (640, 800))
            self.assertEqual(data[8:], enlarged)
        finally:
            a.close()
            b.close()

    def test_nbis_twofold_bridge(self):
        # 128x160 protocol check using synthetic, non-biometric 64x80 data.
        pixels = bytes(i % 256 for i in range(5120))
        enlarged = bridge.enlarge(pixels, scale=2, interpolation="linear")
        self.assertEqual(len(enlarged), 128 * 160)
        sent = bytearray()

        class Collector:
            def sendall(self, data):
                sent.extend(data)

        bridge.send_image(Collector(), enlarged, scale=2)
        self.assertEqual(struct.unpack("=ii", sent[:8]), (128, 160))
        self.assertEqual(sent[8:], enlarged)

    def test_scale_one_pass_through(self):
        pixels = bytes(i % 256 for i in range(5120))
        self.assertEqual(bridge.enlarge(pixels, scale=1), pixels)
        with self.assertRaises(ValueError):
            bridge.enlarge(pixels, scale=0)
        with self.assertRaises(ValueError):
            bridge.send_image(None, pixels, scale=10)


if __name__ == "__main__":
    unittest.main()
