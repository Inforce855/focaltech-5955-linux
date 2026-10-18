#!/usr/bin/env python3
"""Offline real-gateway protocol regressions; dummy subprocess, zero-only frames.

Never accesses hardware, a proprietary DLL, systemd, PAM or user fingerprints.
"""
import importlib.util
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
GATEWAY=ROOT/"tools/ft5955_dev_template_gateway.py"
LAUNCHER=ROOT/"tools/ft5955_dev_template_launcher.py"

# Minimal subprocess speaking the exact binary protocol of template_session.c.
# This FAKE must never be deployed or permitted to authenticate a user.
FAKE=r"""
import struct,sys
inp=sys.stdin.buffer
out=sys.stdout.buffer
def line(s):
    out.write(s.encode()+b'\n');out.flush()
line('READY')
mode=''
while True:
    cmd=inp.read(1)
    if not cmd or cmd==b'Q':
        line('DONE');break
    if cmd==b'I':
        hdr=inp.read(5)
        size=int.from_bytes(hdr[:4],'little')
        if not 1<=size<=1048576 or len(inp.read(size))!=size:
            sys.exit(2)
        mode='V';line('IMPORTED')
    elif cmd in (b'E',b'V'):
        frame=inp.read(5120)
        if len(frame)!=5120:
            sys.exit(3)
        if cmd==b'E':
            line('PROGRESS 1 12')
        else:
            line('NO_MATCH')
    else:
        sys.exit(4)
"""

class BinaryStream:
    def __init__(self,data=b""):
        self.buffer=io.BytesIO(data)

def load_module():
    spec=importlib.util.spec_from_file_location("ft5955_dev_template_gateway_test",GATEWAY)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

class ProtocolTests(unittest.TestCase):
    def exchange(self, request: bytes) -> bytes:
        gateway=load_module()
        real_engine=gateway.Engine
        with tempfile.TemporaryDirectory() as tmp:
            fake=Path(tmp)/"fake.py"
            fake.write_text(FAKE,encoding="utf-8")
            def substitute(_ignored):
                return real_engine([sys.executable,str(fake)])
            src=BinaryStream(request)
            dst=BinaryStream()
            argv=["gateway","--moh-dir","/opt/ft5955-dev"]
            # Never weaken any production runtime checks: only monkeypatch
            # module-local gateway subprocess and fixed-path existence in CI.
            old_exists=Path.is_file
            def fake_is_file(path):
                if str(path)=="/opt/ft5955-dev/live-template":
                    return True
                return old_exists(path)
            with mock.patch.object(gateway,"Engine",side_effect=substitute), \
                 mock.patch.object(sys,"stdin",src), \
                 mock.patch.object(sys,"stdout",dst), \
                 mock.patch.object(sys,"argv",argv), \
                 mock.patch.object(Path,"is_file",fake_is_file):
                self.assertEqual(gateway.main(),0)
            return dst.buffer.getvalue()

    def test_enrol_progress_without_match(self):
        result=self.exchange(b"MODE E\nFRAME\n"+bytes(5120)+b"QUIT\n")
        self.assertEqual(result,b"READY 1\nPROGRESS 1 12\nBYE\n")
        self.assertNotIn(b"MATCH",result)

    def test_wrong_finger_no_match(self):
        result=self.exchange(b"MODE V 3 0\nabcFRAME\n"+bytes(5120)+b"QUIT\n")
        self.assertEqual(result,b"READY 1\nNO_MATCH\nBYE\n")

    def test_pinned_sha_ast_reader(self):
        spec=importlib.util.spec_from_file_location("ft5955_pin_reader",LAUNCHER)
        launcher=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(launcher)
        with tempfile.TemporaryDirectory() as tmp:
            fixture=Path(tmp)/"preflight.py"
            fixture.write_text("PIN = "+repr("a"*64)+chr(10),encoding="utf-8")
            with mock.patch.object(launcher,"PREFLIGHT",fixture), \
                 mock.patch.object(launcher,"trusted",return_value=None):
                self.assertEqual(launcher.dll_pin(),"a"*64)

    def test_service_unit_points_to_real_protocol(self):
        unit=(ROOT/"systemd/ft5955-engine-dev-protocol.service").read_text()
        self.assertIn("ft5955_dev_protocol_server.py",unit)
        self.assertIn("RestrictAddressFamilies=AF_UNIX AF_NETLINK",unit)
        self.assertIn("NoNewPrivileges=yes",unit)
        self.assertNotIn("ft5955_dev_mock_server.py",unit)

if __name__=="__main__":
    unittest.main()
