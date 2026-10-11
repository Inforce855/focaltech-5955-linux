"""Offline, synthetic unit tests: no physical USB device is accessed."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from protocol_codec import ProtocolError, decode_reply, encode_command, xor_bcc


class TestProtocolCodec(unittest.TestCase):
    def test_firmware_info_command(self):
        self.assertEqual(encode_command(0x30), bytes.fromhex("02 00 01 30 31"))

    def test_payload_command(self):
        self.assertEqual(
            encode_command(0x40, b"\x01\x02"),
            bytes.fromhex("02 00 03 40 01 02 40")
        )

    def test_bcc(self):
        self.assertEqual(xor_bcc(bytes.fromhex("00 01 30")), 0x31)

    def test_synthetic_reply(self):
        body = bytes.fromhex("00 04 04") + b"APP"
        frame = bytes([0x02]) + body + bytes([xor_bcc(body)])
        reply = decode_reply(frame)
        self.assertEqual(reply.payload, b"APP")
        self.assertEqual(reply.reply_type, 4)

    def test_short_frame(self):
        with self.assertRaises(ProtocolError):
            decode_reply(bytes.fromhex("02 00 01 04"))

    def test_bad_checksum(self):
        with self.assertRaises(ProtocolError):
            decode_reply(bytes.fromhex("02 00 01 04 00"))

    def test_bad_type(self):
        with self.assertRaises(ProtocolError):
            decode_reply(bytes.fromhex("02 00 01 03 02"))


if __name__ == "__main__":
    unittest.main()
