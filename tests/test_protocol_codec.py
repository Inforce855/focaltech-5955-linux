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
        self.assertFalse(reply.trailing_zero)

    def test_real_sensor_firmware_reply_with_trailing_zero(self):
        # Genuine IN bytes from FocalTech 2808:5955, 11 October 2026.
        raw = bytes.fromhex(
            "02 00 2e 04 46 54 39 33 36 78 5f 41 50 50 5f 46 "
            "57 33 30 33 32 5f 55 53 42 5f 44 45 43 5f 53 "
            "56 30 2e 35 5f 35 38 34 39 5f 50 6f 77 65 72 "
            "4b 65 79 51 00"
        )
        self.assertEqual(len(raw), 51)
        self.assertEqual(int.from_bytes(raw[1:3], "big"), 46)
        self.assertEqual(xor_bcc(raw[1:49]), 0x51)
        reply = decode_reply(raw)
        self.assertEqual(reply.reply_type, 0x04)
        self.assertEqual(
            reply.payload, b"FT936x_APP_FW3032_USB_DEC_SV0.5_5849_PowerKey"
        )
        self.assertTrue(reply.trailing_zero)

    def test_unnamed_trailing_byte_is_rejected(self):
        body = bytes.fromhex("00 02 04 41")
        valid = b"\x02" + body + bytes([xor_bcc(body)])
        with self.assertRaises(ProtocolError):
            decode_reply(valid + b"\x01")

    def test_two_trailing_zeros_are_rejected(self):
        body = bytes.fromhex("00 02 04 41")
        valid = b"\x02" + body + bytes([xor_bcc(body)])
        with self.assertRaises(ProtocolError):
            decode_reply(valid + b"\x00\x00")

    def test_trailing_zero_does_not_hide_bad_checksum(self):
        body = bytes.fromhex("00 02 04 41")
        corrupt = b"\x02" + body + bytes([xor_bcc(body) ^ 1])
        with self.assertRaises(ProtocolError):
            decode_reply(corrupt + b"\x00")

    def test_candidate_finger_status_command(self):
        # ff_sc_ReadFingerStatus in MOH DLL: command 82, argument bytes 73 01.
        # This checks construction ONLY; it is not a hardware response.
        self.assertEqual(
            encode_command(0x82, bytes.fromhex("73 01")),
            bytes.fromhex("02 00 03 82 73 01 f3"),
        )

    def test_synthetic_one_byte_status_reply(self):
        # Illustrative status value only; meaning of 05 remains unverified.
        body = bytes.fromhex("00 02 04 05")
        framed = bytes([0x02]) + body + bytes([xor_bcc(body)])
        self.assertEqual(decode_reply(framed).payload, bytes([0x05]))

    def test_real_no_finger_status_reply(self):
        # Actual 2808:5955 no-finger response, 11 October 2026.
        # USB bulk IN returned a complete 6-byte frame plus one 00 suffix.
        raw = bytes.fromhex("02 00 02 04 06 00 00")
        self.assertEqual(xor_bcc(raw[1:5]), raw[5])
        reply = decode_reply(raw)
        self.assertEqual(reply.reply_type, 0x04)
        self.assertEqual(reply.payload, bytes([0x06]))
        self.assertTrue(reply.trailing_zero)

    def test_real_finger_on_status_reply(self):
        # Actual 2808:5955 finger-on response, 11 October 2026.
        # Same command as no-finger test; 05 instead of 06.
        raw = bytes.fromhex("02 00 02 04 05 03 00")
        self.assertEqual(xor_bcc(raw[1:5]), raw[5])
        reply = decode_reply(raw)
        self.assertEqual(reply.reply_type, 0x04)
        self.assertEqual(reply.payload, bytes([0x05]))
        self.assertTrue(reply.trailing_zero)

    def test_candidate_image_height_request(self):
        # MOH DLL helper 0x180008328 queries selector 03, length 01.
        self.assertEqual(
            encode_command(0x80, bytes.fromhex("03 01")),
            bytes.fromhex("02 00 03 80 03 01 81"),
        )

    def test_candidate_image_width_request(self):
        # MOH DLL helper 0x180008328 queries selector 04, length 01.
        self.assertEqual(
            encode_command(0x80, bytes.fromhex("04 01")),
            bytes.fromhex("02 00 03 80 04 01 86"),
        )

    def test_real_sensor_height_64_reply(self):
        # Actual 2808:5955 height reply, 11 October 2026.
        raw = bytes.fromhex("02 00 02 04 40 46 00")
        self.assertEqual(xor_bcc(raw[1:5]), raw[5])
        reply = decode_reply(raw)
        self.assertEqual(reply.reply_type, 0x04)
        self.assertEqual(reply.payload, bytes([64]))
        self.assertTrue(reply.trailing_zero)

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
