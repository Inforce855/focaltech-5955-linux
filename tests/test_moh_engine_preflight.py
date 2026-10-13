"""Synthetic offline tests for 5955 WinBio engine import preflight."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from moh_engine_preflight import imports_from_objdump, registered_shims

class ImportTests(unittest.TestCase):
    def test_named_imports_only(self):
        sample = """The Import Tables (interpreted .rdata section contents)
 DLL Name: KERNEL32.dll
 001af040  <none>  036c  HeapAlloc
 001af048  <none>  0471  QueryPerformanceCounter
 DLL Name: ADVAPI32.dll
 001af000  <none>  0281  RegOpenKeyExA
The Export Tables (interpreted .rdata section contents)
 001af020  <none>  0001  NOT_IMPORT
"""
        self.assertEqual(imports_from_objdump(sample), [
            ("KERNEL32.dll", "HeapAlloc"),
            ("KERNEL32.dll", "QueryPerformanceCounter"),
            ("ADVAPI32.dll", "RegOpenKeyExA")])

    def test_empty_input(self):
        self.assertEqual(imports_from_objdump("not a PE"), [])

    def test_registered_names(self):
        source = 'R(HeapAlloc);R(TlsFree);reg("InitializeCriticalSection",sh_InitCS);'
        self.assertEqual(registered_shims(source), {
            "HeapAlloc", "TlsFree", "InitializeCriticalSection"})

    def test_missing_does_not_get_covered(self):
        imported = [("KERNEL32.dll", "HeapAlloc"), ("SETUPAPI.dll", "SetupDiEnumDeviceInfo")]
        names = registered_shims("R(HeapAlloc);")
        self.assertEqual([(d, f) for d, f in imported if f not in names],
                         [("SETUPAPI.dll", "SetupDiEnumDeviceInfo")])

if __name__ == "__main__":
    unittest.main()
