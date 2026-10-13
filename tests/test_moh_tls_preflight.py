"""No-proprietary-DLL tests for the read-only MOH PE32+ TLS parser."""
from __future__ import annotations

import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from moh_tls_preflight import PeImage

BASE = 0x180000000


def fixture(callbacks=(0x1300, 0x1380), tls=True, terminate=True):
    data = bytearray(0x800)
    struct.pack_into("<H", data, 0, 0x5a4d)
    struct.pack_into("<I", data, 0x3c, 0x80)
    data[0x80:0x84] = b"PE\x00\x00"
    struct.pack_into("<H", data, 0x84, 0x8664)
    struct.pack_into("<H", data, 0x86, 1)
    struct.pack_into("<H", data, 0x94, 0xf0)
    opt = 0x98
    struct.pack_into("<H", data, opt, 0x20b)
    struct.pack_into("<Q", data, opt + 24, BASE)
    struct.pack_into("<I", data, opt + 56, 0x3000)
    struct.pack_into("<I", data, opt + 60, 0x400)
    struct.pack_into("<I", data, opt + 108, 16)
    section = opt + 0xf0
    data[section:section+8] = b".rdata\x00\x00"
    struct.pack_into("<I", data, section + 8, 0x400)
    struct.pack_into("<I", data, section + 12, 0x1000)
    struct.pack_into("<I", data, section + 16, 0x400)
    struct.pack_into("<I", data, section + 20, 0x400)
    if tls:
        struct.pack_into("<II", data, opt + 112 + 9 * 8, 0x1100, 40)
        pos = 0x500  # RVA 0x1100
        struct.pack_into("<Q", data, pos, BASE + 0x1200)
        struct.pack_into("<Q", data, pos + 8, BASE + 0x1208)
        struct.pack_into("<Q", data, pos + 16, BASE + 0x1210)
        struct.pack_into("<Q", data, pos + 24, BASE + 0x1180)
        struct.pack_into("<I", data, pos + 32, 16)
        struct.pack_into("<I", data, pos + 36, 0)
        callbacks_pos = 0x580
        for i, callback_rva in enumerate(callbacks):
            struct.pack_into("<Q", data, callbacks_pos + 8*i, BASE + callback_rva)
        if terminate:
            struct.pack_into("<Q", data, callbacks_pos + 8*len(callbacks), 0)
    return data


class OfflineTlsTests(unittest.TestCase):
    def test_two_callbacks(self):
        parsed = PeImage(bytes(fixture())).parse_tls()
        self.assertEqual(parsed["tls_rva"], 0x1100)
        self.assertEqual(parsed["template_bytes"], 8)
        self.assertEqual(parsed["zero_fill_bytes"], 16)
        self.assertEqual(parsed["index_va"], BASE + 0x1210)
        self.assertEqual(parsed["callbacks_va"], BASE + 0x1180)
        self.assertEqual(parsed["callbacks"], [BASE + 0x1300, BASE + 0x1380])

    def test_valid_empty_callback_table(self):
        self.assertEqual(PeImage(bytes(fixture(callbacks=()))).parse_tls()["callbacks"], [])

    def test_no_tls_directory(self):
        self.assertIsNone(PeImage(bytes(fixture(tls=False))).parse_tls())

    def test_bad_tls_directory_rva(self):
        data = fixture()
        struct.pack_into("<I", data, 0x98 + 112 + 9 * 8, 0x5000)
        with self.assertRaises(ValueError):
            PeImage(bytes(data)).parse_tls()

    def test_index_and_callback_addresses_must_be_mappable(self):
        data = fixture()
        struct.pack_into("<Q", data, 0x500 + 16, BASE + 0x4400)
        with self.assertRaises(ValueError):
            PeImage(bytes(data)).parse_tls()
        data = fixture()
        struct.pack_into("<Q", data, 0x500 + 24, BASE + 0x4400)
        with self.assertRaises(ValueError):
            PeImage(bytes(data)).parse_tls()

    def test_callback_outside_image(self):
        data = fixture()
        struct.pack_into("<Q", data, 0x580, BASE + 0x5500)
        with self.assertRaises(ValueError):
            PeImage(bytes(data)).parse_tls()

    def test_reject_nonterminated_callback_list(self):
        # 33 consecutive nonzero entries; the parser's maximum is 32.
        data = fixture(callbacks=tuple(0x1300 for _ in range(33)),
                       terminate=False)
        with self.assertRaises(ValueError):
            PeImage(bytes(data)).parse_tls()

    def test_reject_pe32_and_truncated_file(self):
        data = fixture()
        struct.pack_into("<H", data, 0x98, 0x10b)
        with self.assertRaises(ValueError):
            PeImage(bytes(data))
        with self.assertRaises(ValueError):
            PeImage(bytes(fixture()[:0x300]))


if __name__ == "__main__":
    unittest.main()
