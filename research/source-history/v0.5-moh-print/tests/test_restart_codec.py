"""Synthetic C MOH restart across the versioned print envelope."""
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parent.parent
V04=Path.home()/'Projects/ft5955-moh-template-v0.4'
# Tests can run from original container workspace or installed sibling v0.4.
if not V04.is_dir():V04=ROOT.parent/'ft5955-moh-template-v0.4'
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(V04))
from print_codec import encode,decode,wipe

class TestRestart(unittest.TestCase):
    def test_restart_using_envelope(self):
        if not shutil.which('cc'):self.skipTest('No C compiler')
        if not (V04/'template_restart_client.py').is_file():
            self.skipTest('v0.4 restart fixture absent')
        from template_restart_client import PrivateEngine
        with tempfile.TemporaryDirectory() as td:
            binary=Path(td)/'engine'
            subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror',
                '-I',str(V04/'tests'),str(V04/'template_session.c'),
                str(V04/'tests/mock_engine.c'),'-o',str(binary)],check=True)
            cmd=[str(binary),'--live-identify','/tmp/mock']
            a=PrivateEngine(cmd,timeout=4)
            packet=env=restored=None
            try:
                a.start()
                self.assertEqual(a.ask('SAMPLE',bytes(5120)),'RETRY QUALITY')
                for n in range(12):
                    response=a.ask('SAMPLE',bytes([7])*5120)
                    self.assertEqual(response,f'PROGRESS {n+1} 12' if n<11 else 'COMPLETE')
                packet=a.export_template()
                n=struct.unpack_from('<I',packet)[0]
                self.assertEqual(n,len(packet)-5)
                env=encode(memoryview(packet)[5:],packet[4])
                wipe(packet);packet=None
            finally:
                a.close()
            b=PrivateEngine(cmd,timeout=4)
            try:
                b.start()
                template,sub=decode(env)
                restored=bytearray(struct.pack('<IB',len(template),sub))
                restored.extend(template)
                wipe(template)
                b.import_template(restored)
                wipe(restored);restored=None
                self.assertEqual(b.ask('VERIFY',bytes([7])*5120),'MATCH 1')
                self.assertEqual(b.ask('VERIFY',bytes([13])*5120),'NO_MATCH')
                self.assertEqual(b.ask('VERIFY',bytes(5120)),'RETRY QUALITY')
            finally:
                b.close()
                if packet is not None:wipe(packet)
                if restored is not None:wipe(restored)
                if env is not None:wipe(env)

if __name__=='__main__':unittest.main()
