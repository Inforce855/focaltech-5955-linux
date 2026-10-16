#!/usr/bin/env python3
"""Synthetic only: fake sensor stream through actual IPC mock adapter."""
from __future__ import annotations
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from live_capture_client import AdapterClient, capture_batch, read_record


def fake_raw_to_grey(_raw):
    return bytes([7])+bytes(5119)


class CaptureClientTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.runner=Path(self.temp.name)/'mock.sh'
        self.runner.write_text('#!/bin/bash\nexec "'+sys.executable+'" "'+str(ROOT/'fake_vendor_runner.py')+'"\n')
        self.client=AdapterClient([sys.executable,str(ROOT/'moh_adapter.py'),
                                   '--runner',str(self.runner),'--timeout','5'])
        self.client.start()
        self.helper=[sys.executable,str(ROOT/'tests/fake_capture_helper.py')]

    def tearDown(self):
        self.client.close()
        self.temp.cleanup()

    def test_two_finger_capture_pipeline(self):
        for slot in (1,2):
            self.assertEqual(self.client.ask(f'BEGIN {slot}'),'BEGIN OK')
            done, sent, rejected=capture_batch(self.client,'SAMPLE',self.helper,
                                               fake_raw_to_grey)
            self.assertFalse(done)
            self.assertEqual((sent,rejected),(8,0))
            done, sent, rejected=capture_batch(self.client,'SAMPLE',self.helper+['4'],
                                               fake_raw_to_grey)
            self.assertTrue(done)
            self.assertEqual((sent,rejected),(4,0))
        done, sent, rejected=capture_batch(self.client,'VERIFY',self.helper+['1'],
                                           lambda raw: bytes([1])+bytes(5119),first_only=True)
        self.assertTrue(done)
        self.assertEqual(sent,1)

    def test_frame_size_rejection(self):
        self.assertRaises(RuntimeError,lambda: list([read_record(io.BytesIO(b'F\x00\x01x'))]))


if __name__=='__main__':
    unittest.main(verbosity=2)
