"""Offline safety regression for the separate IDENTIFY V2 live-trial script.

No USB, root access, systemd/PAM mutation, prints or vendor matcher execution.
"""
from pathlib import Path
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "ft5955_identify_v2_trial.sh"
ORIGINAL = "02403d764535bc77a83c62c4f696af3e5d4dc8df8b087e74f70989cfa96b1a28"
V1 = "70609faa6783d9175c2925f1cccdcde9a81282fc275b2626185e3bfc2b365bdd"
V2 = "ad0ff83b5e515711eba822dc7ab69f24ab6f6c5764b0f5daed96a609c96666a9"


class IdentifyV2TrialSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = SCRIPT.read_text(encoding="utf-8")

    def test_bash_syntax(self):
        subprocess.run(["bash", "-n", str(SCRIPT)], check=True, capture_output=True)

    def test_v2_stage_and_pinned_original_rollback(self):
        src = self.text
        self.assertEqual(src.count(ORIGINAL), 1)
        self.assertEqual(src.count(V2), 1)
        self.assertNotIn(V1, src)
        self.assertIn('stage-identify-v2', src)
        self.assertNotIn('STAGE="$HOME_DIR/.local/state/ft5955-system-trial/stage-identify"', src)
        self.assertIn('BACK_DIR="$ROOT/.identify-rollback-20261019"', src)
        self.assertIn('    backup_ok\n    ;;\n  --rollback)', src)
        self.assertIn('atomic_library "$BACK_LIB" "$OLD"', src)
        self.assertIn('atomic_marker "$OLD"', src)
        self.assertIn('$(sha "$STAGED")" == "$NEW"', src)

    def test_prior_original_backup_is_never_overwritten(self):
        src = self.text
        for forbidden in (
            'mkdir -m 0700 -- "$BACK_DIR"',
            'install -m 0600 -o root -g root -- "$LIVE" "$BACK_LIB"',
            'install -m 0600 -o root -g root -- "$MARK" "$BACK_MARK"',
        ):
            self.assertNotIn(forbidden, src)
        self.assertLess(src.index('    backup_ok\n    ;;\n  --rollback)'),
                        src.index('  atomic_library "$STAGED" "$NEW"'))
        self.assertIn('[[ "$(sha "$BACK_LIB")" == "$OLD"', src)

    def test_no_auth_or_daemon_mutation(self):
        src = self.text
        self.assertNotRegex(src, r'\bsystemctl\s+(start|stop|restart|enable|disable|mask)\b')
        self.assertNotRegex(src, r'\bauthselect\s+(enable|disable|select)\b')
        self.assertNotIn('fprintd-delete', src)
        self.assertNotIn('fprintd-enroll', src)
        self.assertIn('idle\n', src)
        self.assertIn('known_service\n', src)
        self.assertIn('[[ "$(sha "$LIVE")" == "$OLD"', src)
        self.assertEqual(len(re.findall(r'\bmv -fT -- ', src)), 2)


if __name__ == "__main__":
    unittest.main()
