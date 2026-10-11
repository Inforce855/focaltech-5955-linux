"""All tests use synthetic patterns: no USB, real fingerprints, or biometrics."""
import math
from pathlib import Path
import random
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from fingerprint_compare import (
    WIDTH, HEIGHT, compare, correlation_shift, load_capture,
    preprocess_samples, recent_three,
)


def pattern(seed: int = 0) -> tuple[int, ...]:
    rng = random.Random(seed)
    # Two-dimensional ridge-like synthetic surfaces with different centre.
    cx = 35 + (seed * 13) % 20
    cy = 30 + (seed * 9) % 15
    img = []
    for y in range(HEIGHT):
        for x in range(WIDTH):
            r = math.hypot(x - cx, 1.3 * (y - cy))
            v = 25000 + 5500 * math.sin(r * 1.7 + seed * .13) + 2700 * math.sin(x * .19 + y * .14)
            v += rng.gauss(0, 50)
            img.append(int(min(65535, max(0, v))))
    return tuple(img)


def shifted(image: tuple[int, ...], dx: int, dy: int) -> tuple[int, ...]:
    result = []
    for y in range(HEIGHT):
        for x in range(WIDTH):
            sx, sy = x - dx, y - dy
            if 0 <= sx < WIDTH and 0 <= sy < HEIGHT:
                result.append(image[sy * WIDTH + sx])
            else:
                result.append(20000)
    return tuple(result)


class FingerprintCompareTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.a = preprocess_samples(pattern())
        cls.b = preprocess_samples(pattern(7))

    def test_self_correlation(self):
        r = compare(self.a, self.a)
        self.assertAlmostEqual(r.correlation, 1.0, places=5)
        self.assertEqual((r.dx, r.dy), (0, 0))

    def test_translation(self):
        moved = preprocess_samples(shifted(pattern(), 3, -2))
        r = compare(self.a, moved)
        self.assertGreater(r.correlation, .70)
        self.assertEqual((r.dx, r.dy), (3, -2))

    def test_identity_like_control_ranking(self):
        moved = preprocess_samples(shifted(pattern(), 2, 1))
        same = compare(self.a, moved).correlation
        different = compare(self.a, self.b).correlation
        self.assertGreater(same, different + .15)

    def test_brightness_scaling(self):
        transformed = tuple(min(65535, 1000 + int(v * 1.1)) for v in pattern())
        p = preprocess_samples(transformed)
        self.assertGreater(compare(self.a, p).correlation, .95)

    def test_reject_constant(self):
        with self.assertRaises(ValueError):
            preprocess_samples((35000,) * (WIDTH * HEIGHT))

    def test_malformed_samples(self):
        with self.assertRaises(ValueError):
            preprocess_samples((1, 2, 3))

    def test_invalid_shift(self):
        with self.assertRaises(ValueError):
            compare(self.a, self.b, max_shift=12)

    def test_decode_big_and_little_distinct(self):
        with tempfile.TemporaryDirectory() as t:
            file = Path(t) / 'sample.raw'
            vals = pattern()
            file.write_bytes(struct.pack('>' + str(len(vals)) + 'H', *vals))
            big = load_capture(file, 'big')
            little = load_capture(file, 'little')
            self.assertNotEqual(big.data, little.data)

    def test_bad_size_refused(self):
        with tempfile.TemporaryDirectory() as t:
            file = Path(t) / 'sample.raw'
            file.write_bytes(b'bad')
            with self.assertRaises(ValueError):
                load_capture(file, 'big')

    def test_recent_three_sorted_by_mtime(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            for name in ['fingerprint_a.raw', 'fingerprint_b.raw', 'fingerprint_c.raw', 'fingerprint_d.raw']:
                (d / name).write_bytes(b'raw')
            got = [p.name for p in recent_three(d)]
            self.assertEqual(got, ['fingerprint_b.raw', 'fingerprint_c.raw', 'fingerprint_d.raw'])


if __name__ == '__main__':
    unittest.main()
