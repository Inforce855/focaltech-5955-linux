"""Synthetic-only codec tests; never use real biometric data or hardware."""
from __future__ import annotations
import ctypes
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from print_codec import encode, decode, wipe, HEADER

class CTemplate(ctypes.Structure):
    _fields_ = [('bytes',ctypes.POINTER(ctypes.c_uint8)),
                ('length',ctypes.c_size_t),('subfactor',ctypes.c_uint8)]

class TestCodec(unittest.TestCase):
    def setUp(self):
        self.source=bytearray((i*29+7)%256 for i in range(337))  # Synthetic
    def tearDown(self):
        wipe(self.source)
    def test_python_roundtrip(self):
        env=encode(self.source,17)
        result,sub=decode(env)
        self.assertEqual(result,self.source)
        self.assertEqual(sub,17)
        wipe(result);wipe(env)
    def test_bad_inputs(self):
        env=encode(self.source,13)
        for pos in [0,8,9,11,12,13,14,15,16,20,len(env)-1]:
            copy=bytearray(env);copy[pos]^=0x01
            with self.subTest(pos=pos),self.assertRaises(ValueError):decode(copy)
            wipe(copy)
        for size in (0,1,HEADER.size+32,len(env)-1):
            with self.subTest(size=size),self.assertRaises(ValueError):decode(env[:size])
        bad=bytearray(env)
        bad[16:20]=struct.pack('<I',1048577)
        with self.assertRaises(ValueError):decode(bad)
        wipe(bad);wipe(env)
    def test_max_and_rejection(self):
        with self.assertRaises(ValueError):encode(b'',0)
        with self.assertRaises(ValueError):encode(b'a'*1048577,0)
        with self.assertRaises(ValueError):encode(b'a',256)
    def test_c_interop(self):
        if not shutil.which('cc'):self.skipTest('No C compiler')
        with tempfile.TemporaryDirectory() as td:
            so=Path(td)/'libprintcodec.so'
            subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror',
                 '-shared','-fPIC','-I',str(ROOT/'driver'),str(ROOT/'driver/ft5955_print_codec.c'),
                 '-lcrypto','-o',str(so)],check=True)
            lib=ctypes.CDLL(str(so))
            ptr=ctypes.POINTER(ctypes.c_uint8)
            lib.ft5955_print_pack.argtypes=[ptr,ctypes.c_size_t,ctypes.c_uint8,
                                             ctypes.POINTER(ptr),ctypes.POINTER(ctypes.c_size_t)]
            lib.ft5955_print_pack.restype=ctypes.c_int
            lib.ft5955_print_unpack.argtypes=[ptr,ctypes.c_size_t,ctypes.POINTER(CTemplate)]
            lib.ft5955_print_unpack.restype=ctypes.c_int
            lib.ft5955_free_sensitive.argtypes=[ctypes.c_void_p,ctypes.c_size_t]
            lib.ft5955_print_template_clear.argtypes=[ctypes.POINTER(CTemplate)]
            source=(ctypes.c_uint8*len(self.source)).from_buffer(self.source)
            out=ptr();length=ctypes.c_size_t()
            self.assertEqual(lib.ft5955_print_pack(source,len(self.source),91,
                                                     ctypes.byref(out),ctypes.byref(length)),0)
            buffer=bytearray(ctypes.string_at(out,length.value))
            lib.ft5955_free_sensitive(out,length.value)
            data,sub=decode(buffer)
            self.assertEqual(data,self.source)
            self.assertEqual(sub,91)
            wipe(data)
            self.assertEqual(buffer,encode(self.source,91))
            arr=(ctypes.c_uint8*len(buffer)).from_buffer(buffer)
            recovered=CTemplate()
            self.assertEqual(lib.ft5955_print_unpack(arr,len(buffer),ctypes.byref(recovered)),0)
            self.assertEqual(ctypes.string_at(recovered.bytes,recovered.length),bytes(self.source))
            self.assertEqual(recovered.subfactor,91)
            lib.ft5955_print_template_clear(ctypes.byref(recovered))
            buffer[-1]^=1
            self.assertNotEqual(lib.ft5955_print_unpack(arr,len(buffer),ctypes.byref(recovered)),0)
            self.assertFalse(bool(recovered.bytes))
            wipe(buffer)

if __name__=='__main__':unittest.main()
