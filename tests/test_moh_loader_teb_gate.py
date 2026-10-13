"""Guard regression checks: inspect the MOH loader source, never run the DLL.

These tests intentionally do not call ft_engine_smoke_interface or load_pe.
They verify the sequence and gates of the *still disabled* experimental path.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "engine" / "ft_engine.c").read_text(encoding="utf-8")
BUILD = (ROOT / "tools" / "build_moh_engine_smoke.sh").read_text(encoding="utf-8")
START = SOURCE.index("static int __attribute__((unused)) load_pe(void)")
END = SOURCE.index("// find an export by name", START)
LOADER = SOURCE[START:END]


class GatedTebWiring(unittest.TestCase):
    def test_private_thread_layout_linked(self):
        self.assertIn('#include "ft5955_compat_teb_layout.h"', SOURCE)
        self.assertIn("ft5955_teb_prepare_current()", SOURCE)
        self.assertIn("ft5955_teb_view_current()", SOURCE)
        self.assertIn("engine/ft5955_compat_teb_layout.c", BUILD)

    def test_no_shared_dummy_stack_or_legacy_tls_callback_execution(self):
        self.assertNotIn("g_teb[", SOURCE)
        self.assertNotIn("g_peb[", SOURCE)
        self.assertNotIn("g_tls_block[", SOURCE)
        self.assertNotIn("cbaddr", LOADER)
        self.assertNotIn("g_tls_array", LOADER)
        self.assertIn('if(tlsrva){', LOADER)
        self.assertIn("PE TLS directory/callbacks not audited", LOADER)
        self.assertLess(LOADER.index("if(tlsrva){"), LOADER.index("g_image=m;"))

    def test_import_gate_and_thread_setup_before_dllmain(self):
        self.assertLess(LOADER.index("if(unresolved_imports)"),
                        LOADER.index("if(set_engine_gs_current()!=0)"))
        self.assertLess(LOADER.index("if(set_engine_gs_current()!=0)"),
                        LOADER.index("int r=DllMain("))

    def test_no_runtime_gate_removed(self):
        self.assertIn("#ifndef FT5955_ALLOW_DLL_EXECUTION_AFTER_AUDIT", SOURCE)
        self.assertIn("#ifndef FT5955_ALLOW_UNVERIFIED_ATTACH", SOURCE)
        self.assertIn('return -100;', SOURCE)


if __name__ == "__main__":
    unittest.main()
