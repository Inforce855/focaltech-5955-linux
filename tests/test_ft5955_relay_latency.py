"""Synthetic relay latency regression with deliberately open parent stdin.

Only fake 5,120-byte payloads and mock MODE E/RETRY QUALITY/BYE messages.
Exercises the actual non-root relay and broker, never a fingerprint or MOH DLL.
"""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
BROKER = ROOT / "tools" / "ft5955_engine_broker.py"
sys.path.insert(0, str(ROOT / "tools"))
from test_ft5955_engine_broker_synthetic import MOCK_GATEWAY, FRAME_SIZE


@unittest.skipIf(os.geteuid() == 0, "Must never run as root")
class RelayLatencyTests(unittest.TestCase):
    def test_does_not_wait_one_second_for_open_stdin_after_gateway_bye(self):
        with tempfile.TemporaryDirectory(prefix="ft5955-relay-latency-") as root_name:
            root = Path(root_name)
            root.chmod(0o700)
            gateway = root / "mock_gateway.py"
            gateway.write_text(MOCK_GATEWAY, encoding="utf-8")
            gateway.chmod(0o600)
            sock = root / "engine.sock"
            server = subprocess.Popen([
                sys.executable, str(BROKER), "--serve", "--test-only",
                "--socket", str(sock), "--gateway", str(gateway),
                "--moh-dir", str(root),
            ], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE)
            client = None
            try:
                deadline = time.monotonic() + 6
                while not sock.exists():
                    self.assertIsNone(server.poll(), "Broker exited early")
                    self.assertLess(time.monotonic(), deadline, "Broker socket timeout")
                    time.sleep(0.02)
                client = subprocess.Popen([
                    sys.executable, str(BROKER), "--test-only", "--socket", str(sock)
                ], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                self.assertIsNotNone(client.stdin)
                self.assertIsNotNone(client.stdout)
                # Leave the parent's stdin WRITE END OPEN through process exit.
                # This deliberately leaves relay's daemon os.read(0) blocked.
                client.stdin.write(b"MODE E\nFRAME\n" + bytes(FRAME_SIZE) + b"QUIT\n")
                client.stdin.flush()
                expected = b"READY 1\nRETRY QUALITY\nBYE\n"
                actual = client.stdout.read(len(expected))
                self.assertEqual(actual, expected)
                start = time.monotonic()
                self.assertEqual(client.wait(timeout=4), 0)
                wait_s = time.monotonic() - start
                self.assertLess(
                    wait_s, 0.85,
                    f"Relay waited {wait_s:.3f}s after gateway BYE despite completed session")
                self.assertEqual(server.wait(timeout=5), 0)
            finally:
                if client is not None:
                    if client.poll() is None:
                        client.terminate()
                        try: client.wait(timeout=2)
                        except subprocess.TimeoutExpired:
                            client.kill()
                            client.wait(timeout=2)
                    if client.stdin: client.stdin.close()
                    if client.stdout: client.stdout.close()
                    if client.stderr: client.stderr.close()
                if server.poll() is None:
                    server.terminate()
                    try: server.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        server.kill()
                        server.wait(timeout=2)
                if server.stderr: server.stderr.close()


if __name__ == "__main__":
    unittest.main()
