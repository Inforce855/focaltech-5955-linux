"""Tests for bounded, non-executing 5955 TEB instruction-context collector."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from moh_teb_context import find_contexts


class TestTebContext(unittest.TestCase):
    def test_context_surrounding_direct_and_indirect_accesses(self):
        disassembly = [
            "180001000 <start>:",
            " 180001001:\tpush rbp",
            " 180001003:\tmov rax,QWORD PTR gs:0x30",
            " 18000100b:\tmov rdx,QWORD PTR [rax+0x68]",
            " 18000100f:\tret",
        ]
        count, records = find_contexts(disassembly, before=2, after=2)
        self.assertEqual(count, 1)
        self.assertEqual(records[0]["segment"], "gs")
        self.assertEqual(records[0]["offset"], 0x30)
        self.assertEqual(records[0]["address"], "0x180001003")
        self.assertEqual(len(records[0]["before"]), 1)
        self.assertEqual(len(records[0]["after"]), 2)
        self.assertIn("[rax+0x68]", records[0]["after"][0])

    def test_nearby_hits_get_separate_windows(self):
        lines = [
            " 180001001:\tmov rax,QWORD PTR gs:0x30",
            " 180001002:\tmov rbx,QWORD PTR gs:0x10",
            " 180001003:\tmov rcx,QWORD PTR [rax+0x58]",
            " 180001004:\tret",
        ]
        n, records = find_contexts(lines, before=2, after=2)
        self.assertEqual(n, 2)
        self.assertEqual([x["offset"] for x in records], [0x30, 0x10])
        self.assertEqual(len(records[0]["after"]), 2)
        self.assertEqual(len(records[1]["before"]), 1)
        self.assertEqual(len(records[1]["after"]), 2)

    def test_function_boundary_does_not_invent_continuation(self):
        lines = [
            "1000 <first>:",
            " 1000:\tmov rax,QWORD PTR gs:0x30",
            "1004 <second>:",
            " 1004:\tmov rdx,QWORD PTR [rax+0x68]",
        ]
        n, records = find_contexts(lines, before=4, after=4)
        self.assertEqual(n, 1)
        self.assertEqual(records[0]["after"], [])

    def test_display_limit_does_not_hide_total(self):
        lines = [f" {0x2000 + x:x}:\tmov rax,QWORD PTR gs:0x30"
                 for x in range(5)]
        n, records = find_contexts(lines, before=0, after=1, limit=2)
        self.assertEqual(n, 5)
        self.assertEqual(len(records), 2)


if __name__ == "__main__":
    unittest.main()
