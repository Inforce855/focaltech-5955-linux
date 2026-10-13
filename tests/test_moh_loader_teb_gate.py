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
# Use the next function definition, not a comment that may be reworded.
END = SOURCE.index("static __attribute__((unused)) void* get_export(", START)
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
        self.assertIn("ft5955_pe_guard(g_file,(size_t)g_filelen,&layout)", LOADER)
        self.assertIn("PE headers/sections invalid or unsupported", LOADER)
        self.assertIn("engine/ft5955_pe_guard.c", BUILD)
        self.assertLess(LOADER.index("ft5955_pe_guard("), LOADER.index("img=calloc"))
        self.assertLess(LOADER.index("ft5955_pe_guard("), LOADER.index("g_image=m;"))

    def test_import_walk_is_bounded(self):
        self.assertIn("layout.import_size", LOADER)
        self.assertIn("invalid/unterminated import descriptors", LOADER)
        self.assertIn("invalid import-function name", LOADER)
        self.assertLess(LOADER.index("invalid import-function name"),
                        LOADER.index("int mfd=memfd_create("))

    def test_thread_identifiers_are_not_shared_constants(self):
        self.assertIn('#include "ft5955_compat_identity.h"', SOURCE)
        self.assertIn('reg("GetCurrentProcessId", (void*)ft5955_GetCurrentProcessId)', SOURCE)
        self.assertIn('reg("GetCurrentThreadId", (void*)ft5955_GetCurrentThreadId)', SOURCE)
        self.assertNotIn("return 1234;", SOURCE)
        self.assertNotIn("return 5678;", SOURCE)
        self.assertIn("engine/ft5955_compat_identity.c", BUILD)

    def test_export_resolver_is_bounded(self):
        self.assertIn('#include "ft5955_pe_exports.h"', SOURCE)
        self.assertIn("engine/ft5955_pe_exports.c", BUILD)
        self.assertIn("ft5955_pe_find_export(g_image,g_layout.image_size", SOURCE)
        self.assertIn("BLOCKED: PE export outside executable section", SOURCE)
        self.assertNotIn("u32 nnames=*(u32*)(g_image+exprva+24)", SOURCE)

    def test_import_gate_and_thread_setup_before_dllmain(self):
        self.assertLess(LOADER.index("if(unresolved_imports)"),
                        LOADER.index("if(set_engine_gs_current()!=0)"))
        self.assertLess(LOADER.index("if(set_engine_gs_current()!=0)"),
                        LOADER.index("int r=DllMain("))

    def test_no_runtime_gate_removed(self):
        self.assertIn("#ifndef FT5955_ALLOW_DLL_EXECUTION_AFTER_AUDIT", SOURCE)
        self.assertIn("#if !defined(FT5955_ALLOW_UNVERIFIED_ATTACH) || !defined(FT5955_ALLOW_DLL_EXECUTION_AFTER_AUDIT)", SOURCE)
        self.assertIn('return -100;', SOURCE)


if __name__ == "__main__":
    unittest.main()
