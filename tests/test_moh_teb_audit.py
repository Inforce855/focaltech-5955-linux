"""Synthetic tests for static MOH x64 TEB/GS disassembly preflight."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from moh_teb_audit import KNOWN_X64_TEB, scan_stream, segment_reference


class SegmentReferenceTests(unittest.TestCase):
    def test_direct_gs_absolute(self):
        self.assertEqual(
            segment_reference("   1800010ab:\tmov    rax,QWORD PTR gs:0x60"),
            ("gs", 0x60, "0x1800010ab"),
        )

    def test_direct_bracket_and_raw_bytes(self):
        self.assertEqual(
            segment_reference(" 180001022: 65 48 8b 04 25 30 00 00 00\tmov rax,QWORD PTR gs:[0x30]"),
            ("gs", 0x30, "0x180001022"),
        )

    def test_dynamic_index_not_called_constant(self):
        self.assertEqual(
            segment_reference(" 180001044:\tmov rax,QWORD PTR gs:[rcx+0x68]"),
            ("gs", None, "0x180001044"),
        )
        self.assertEqual(
            segment_reference(" 180001055:\tmov rax,QWORD PTR gs:rax"),
            ("gs", None, "0x180001055"),
        )

    def test_fs_and_no_reference(self):
        self.assertEqual(
            segment_reference(" 180001066:\tmov eax,DWORD PTR fs:0x28"),
            ("fs", 0x28, "0x180001066"),
        )
        self.assertIsNone(segment_reference(" 180001088: xor eax,eax"))
        self.assertIsNone(segment_reference("Disassembly of section .text:"))

    def test_counts_and_sample_cap(self):
        lines = [
            " 1800010ab:\tmov rax,QWORD PTR gs:0x60",
            " 1800010ac:\tmov rbx,QWORD PTR gs:0x60",
            " 1800010ad:\tmov rcx,QWORD PTR gs:[rdx+0x40]",
            " 1800010ae:\tmov rcx,QWORD PTR gs:0x68",
        ]
        counts, examples = scan_stream(lines, max_examples=1)
        self.assertEqual(counts[("gs", 0x60)], 2)
        self.assertEqual(examples[("gs", 0x60)], ["0x1800010ab"])
        self.assertEqual(counts[("gs", None)], 1)
        self.assertEqual(counts[("gs", 0x68)], 1)
        self.assertEqual(KNOWN_X64_TEB[0x68], "LastErrorValue")


if __name__ == "__main__":
    unittest.main()
