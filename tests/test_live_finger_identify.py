"""Synthetic-only tests for live two-finger identification's Python protocol.

No vendor engine, USB device, privileged helper or real fingerprint is used.
"""
import pathlib
import sys
import unittest

TOOLS = pathlib.Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))
from live_finger_identify import interpret_response, prepared_pixels


class TestLiveIdentifyFormatting(unittest.TestCase):
    def test_discrete_identification_outcomes(self):
        cases = {
            "IDENTIFY 1": "Finger 1 — MATCH",
            "IDENTIFY 2": "Finger 2 — MATCH",
            "IDENTIFY NONE": "No match to either enrolled finger (experimental result)",
            "IDENTIFY AMBIGUOUS": "AMBIGUOUS — both fingers matched; do not identify this capture",
            "IDENTIFY REJECTED": "Scan rejected; lift, reposition and try again",
        }
        for response, expected in cases.items():
            with self.subTest(response=response):
                self.assertEqual(interpret_response(response), expected)

    def test_unexpected_response_must_not_be_reported_as_match(self):
        for response in ("IDENTIFY 3", "IDENTIFY", "ERROR verification-engine", "",
                         "ENROL 1 COMPLETE", "IDENTIFY 1 EXTRA"):
            with self.subTest(response=response):
                with self.assertRaises(ValueError):
                    interpret_response(response)

    def test_polarity_inversion_uses_exact_image_size(self):
        # A uniform synthetic raw image contrast-stretches to 0 then inverts.
        image = prepared_pixels(bytes(10240))
        self.assertEqual(len(image), 5120)
        self.assertEqual(image, bytes([255]) * 5120)

    def test_truncated_sensor_data_fails_closed(self):
        with self.assertRaises(ValueError):
            prepared_pixels(bytes(10239))


if __name__ == "__main__":
    unittest.main()
