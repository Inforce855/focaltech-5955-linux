#!/usr/bin/env python3
"""Synthetic frames/templates only; never opens USB or proprietary engine."""
from pathlib import Path
import importlib.util
import io
from unittest.mock import patch
import tempfile
import unittest
import sys

ENGINE = Path(__file__).resolve().parents[1]/'engine/engine_gateway.py'
spec=importlib.util.spec_from_file_location('ft_gateway', ENGINE)
gw=importlib.util.module_from_spec(spec)
spec.loader.exec_module(gw)

class Fake:
    def __init__(self,command):
        self.enroll=0
        self.template=None
    def start(self):pass
    def close(self):pass
    def imported(self,template,subfactor):
        assert bytes(template)==b'example synthetic bytes' and subfactor==9
        self.template=bytes(template)
    def frame(self,mode,image):
        assert len(image)==5120
        if mode=='V':return 'MATCH' if image[0]==5 else 'NO_MATCH'
        self.enroll+=1
        if self.enroll==1:return 'RETRY QUALITY'
        if self.enroll==13:return 'COMPLETE'
        return f'PROGRESS {self.enroll-1} 12'
    def exported(self):return bytearray(b'example synthetic bytes'),9

class TestProtocol(unittest.TestCase):
    def run_server(self,wire):
        with tempfile.TemporaryDirectory() as path:
            (Path(path)/'tools').mkdir()
            (Path(path)/'tools/test_moh_isolated_live_identify.sh').touch()
            original_in,original_out,original_argv=sys.stdin,sys.stdout,sys.argv
            input_stream=io.TextIOWrapper(io.BytesIO(wire),encoding='ascii')
            output=io.BytesIO()
            output_stream=io.TextIOWrapper(output,encoding='ascii',write_through=True)
            try:
                sys.stdin=input_stream;sys.stdout=output_stream
                sys.argv=['gateway','--moh-dir',path]
                with patch.object(gw,'Engine',Fake),patch.object(gw.os,'geteuid',return_value=1000):
                    self.assertEqual(gw.main(),0)
                output_stream.flush()
                return output.getvalue()
            finally:
                sys.stdin,sys.stdout,sys.argv=original_in,original_out,original_argv
    def test_enroll_twelve_real_protocol_messages(self):
        wire=b'MODE E\n'+(b'FRAME\n'+bytes(5120))*13+b'QUIT\n'
        result=self.run_server(wire)
        self.assertTrue(result.startswith(b'READY 1\nRETRY QUALITY\nPROGRESS 1 12\n'))
        self.assertIn(b'PROGRESS 11 12\nCOMPLETE\nTEMPLATE 23 9\nexample synthetic bytesBYE\n',result)
    def test_import_and_match(self):
        template=b'example synthetic bytes'
        wire=f'MODE V {len(template)} 9\n'.encode()+template
        wire+=b'FRAME\n'+bytes([5])+bytes(5119)+b'FRAME\n'+bytes(5120)+b'QUIT\n'
        self.assertEqual(self.run_server(wire),b'READY 1\nMATCH\nNO_MATCH\nBYE\n')

if __name__=='__main__':unittest.main(verbosity=2)
