#!/usr/bin/env python3
"""End-to-end synthetic protocol test, including subprocess shutdown."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent


class AdapterTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        # Adapter calls 'bash runner'; script execs the fake Python engine.
        self.runner = Path(self.temp.name) / 'fake.sh'
        self.runner.write_text('#!/bin/bash\nexec "'+sys.executable+'" "'+str(ROOT/'fake_vendor_runner.py')+'"\n')
        self.proc = subprocess.Popen([sys.executable, str(ROOT/'moh_adapter.py'),
                                      '--runner', str(self.runner), '--timeout', '5'],
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE, bufsize=0)

    def tearDown(self):
        if self.proc.poll() is None:
            self.proc.kill()
        self.proc.communicate(timeout=5)
        self.temp.cleanup()

    def ask(self, command, expected, first=None):
        self.proc.stdin.write(command.encode('ascii')+b'\n')
        if first is not None:
            self.proc.stdin.write(bytes([first])+b'\1'*5119)
        self.proc.stdin.flush()
        actual = self.proc.stdout.readline().decode().strip()
        self.assertEqual(actual, expected, command)

    def test_complete_pipeline(self):
        self.ask('HELLO', 'READY 2')
        self.ask('VERIFY', 'ERROR BAD_STATE', 1)
        for slot in (1, 2):
            self.ask(f'BEGIN {slot}', 'BEGIN OK')
            self.ask('SAMPLE', 'RETRY QUALITY', 0)
            for n in range(1, 12):
                self.ask('SAMPLE', f'PROGRESS {n} 12', 7)
            self.ask('SAMPLE', 'COMPLETE', 7)
        for first, result in ((1,'MATCH 1'), (2,'MATCH 2'), (3,'NO_MATCH'),
                              (4,'AMBIGUOUS'), (0,'RETRY QUALITY')):
            self.ask('VERIFY', result, first)
        self.ask('CANCEL', 'CANCELLED')
        self.ask('VERIFY', 'ERROR BAD_STATE', 1)
        self.ask('BEGIN 1', 'BEGIN OK')
        self.ask('SAMPLE', 'PROGRESS 1 12', 7)
        self.ask('QUIT', 'BYE')
        self.assertEqual(self.proc.wait(timeout=5), 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
