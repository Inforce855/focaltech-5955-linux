"""Synthetic test of compiled C engine process and binary memory-only export/import."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from template_restart_client import PrivateEngine, wipe

BASE = Path(__file__).resolve().parent.parent

class TestTemplateBoundary(unittest.TestCase):
    def test_restart_and_verify(self):
        compiler = shutil.which('cc')
        if not compiler:
            self.skipTest('C compiler not available')
        with tempfile.TemporaryDirectory() as td:
            binary = Path(td) / 'engine'
            subprocess.run([compiler, '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
                            '-I', str(BASE / 'tests'), str(BASE / 'template_session.c'),
                            str(BASE / 'tests/mock_engine.c'), '-o', str(binary)],
                           check=True)
            cmd = [str(binary), '--live-identify', '/tmp/synthetic-dll-placeholder']
            a = PrivateEngine(cmd, timeout=4)
            try:
                a.start()
                self.assertEqual(a.ask('SAMPLE', bytes(5120)), 'RETRY QUALITY')
                for i in range(12):
                    reply = a.ask('SAMPLE', bytes([7])*5120)
                    self.assertEqual(reply, f'PROGRESS {i+1} 12' if i<11 else 'COMPLETE')
                tmpl = a.export_template()
                self.assertEqual(len(tmpl), 21)
            finally:
                a.close()
            b = PrivateEngine(cmd, timeout=4)
            try:
                b.start()
                b.import_template(tmpl)
                wipe(tmpl)
                self.assertEqual(a.proc,None)
                self.assertEqual(b.ask('VERIFY',bytes([7])*5120),'MATCH 1')
                self.assertEqual(b.ask('VERIFY',bytes([13])*5120),'NO_MATCH')
                self.assertEqual(b.ask('VERIFY',bytes(5120)),'RETRY QUALITY')
            finally:
                b.close()

if __name__ == '__main__':
    unittest.main()
