"""Synthetic image-transfer tests, with no USB or biometric data access."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))

from image_transfer import (
    RAW_LENGTH, FRAMED_LENGTH, MAX_WIRE_BYTES,
    extract_image, is_complete_transfer, receive_limited,
)
from protocol_codec import ProtocolError, xor_bcc


class TestImageTransfer(unittest.TestCase):
    def setUp(self):
        self.fake = bytes((i % 251 for i in range(RAW_LENGTH)))
        body = (RAW_LENGTH + 1).to_bytes(2, 'big') + b'\x04' + self.fake
        self.framed = b'\x02' + body + bytes([xor_bcc(body)])

    def test_sizes(self):
        self.assertEqual((RAW_LENGTH, FRAMED_LENGTH, MAX_WIRE_BYTES),
                         (10240, 10245, 10246))

    def test_raw(self):
        result = extract_image(self.fake)
        self.assertEqual(result.pixels, self.fake)
        self.assertIn('UNVERIFIED', result.format)
        self.assertTrue(is_complete_transfer(self.fake))

    def test_framed(self):
        self.assertEqual(len(self.framed), FRAMED_LENGTH)
        self.assertEqual(extract_image(self.framed).pixels, self.fake)
        self.assertEqual(extract_image(self.framed + b'\x00').pixels, self.fake)

    def test_real_shape_with_nonzero_trailer(self):
        # Mirrors 10246-byte shape from first hardware image-read test.
        # Contents here are SYNTHETIC. Do not publish live biometrics.
        result = extract_image(self.framed + b'\x7e')
        self.assertEqual(result.pixels, self.fake)
        self.assertIn('nonzero trailer', result.format)

    def test_zero_trailer_still_works(self):
        result = extract_image(self.framed + b'\x00')
        self.assertEqual(result.pixels, self.fake)
        self.assertIn('trailing 00', result.format)

    def test_invalid_checksum_nonzero_trailer_rejected(self):
        invalid = self.framed[:-1] + bytes((self.framed[-1] ^ 1,))
        with self.assertRaises(ProtocolError):
            extract_image(invalid + b'\x7e')

    def test_two_nonzero_trailers_refused(self):
        with self.assertRaises(ProtocolError):
            extract_image(self.framed + b'\x7e\x11')

    def test_invalid_type_with_nonzero_trailer_rejected(self):
        body = (RAW_LENGTH + 1).to_bytes(2, 'big') + b'\x05' + self.fake
        frame = b'\x02' + body + bytes((xor_bcc(body),))
        with self.assertRaises(ProtocolError):
            extract_image(frame + b'\x7e')

    def test_bad_checksum(self):
        with self.assertRaises(ProtocolError):
            extract_image(self.framed[:-1] + bytes([self.framed[-1] ^ 1]))

    def test_partial_framed_refused_even_if_raw_length(self):
        self.assertFalse(is_complete_transfer(self.framed[:RAW_LENGTH]))
        with self.assertRaises(ProtocolError):
            extract_image(self.framed[:RAW_LENGTH])

    def test_small_status_refused(self):
        body = b'\x00\x02\x04\x06'
        packet = b'\x02' + body + bytes([xor_bcc(body)]) + b'\x00'
        self.assertTrue(is_complete_transfer(packet))
        with self.assertRaises(ProtocolError):
            extract_image(packet)

    def test_stream_framed_fragmented(self):
        packets = iter(self.framed[i:i + 64] for i in range(0, len(self.framed), 64))
        collected = receive_limited(lambda size, timeout: next(packets))
        self.assertEqual(extract_image(collected).pixels, self.fake)

    def test_stream_raw_fragmented(self):
        packets = iter(self.fake[i:i + 64] for i in range(0, len(self.fake), 64))
        collected = receive_limited(lambda size, timeout: next(packets))
        self.assertEqual(collected, self.fake)

    def test_oversize_refused(self):
        with self.assertRaises(ProtocolError):
            extract_image(b'\xff' * (MAX_WIRE_BYTES + 1))


if __name__ == '__main__':
    unittest.main()
