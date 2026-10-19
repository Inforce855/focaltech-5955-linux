"""Read-only checks for guarded FT5955 live-library swap.

NO root, USB, PAM or service operations. Runs shell syntax and strict
source contract checks; it is not a substitute for real preflight.
"""
from __future__ import annotations

from pathlib import Path
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "ft5955_identify_live_trial.sh"
OLD = "02403d764535bc77a83c62c4f696af3e5d4dc8df8b087e74f70989cfa96b1a28"
NEW = "70609faa6783d9175c2925f1cccdcde9a81282fc275b2626185e3bfc2b365bdd"


class LiveTrialSourceChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = SCRIPT.read_text(encoding="utf-8")

    def test_bash_syntax(self):
        subprocess.run(["bash", "-n", str(SCRIPT)], check=True, capture_output=True)

    def test_verified_hashes_and_backup_before_swap(self):
        for value in (OLD, NEW):
            self.assertEqual(self.text.count(value), 1)
        for fragment in (
            "set -Eeuo pipefail",
            "umask 077",
            'BACK_DIR="$ROOT/.identify-rollback-20261019"',
            'regular_root "$OVERRIDE90"',
            'regular_root "$OVERRIDE95"',
            'stage_ok',
            'backup_ok',
            'idle',
            '[[ "$(sha "$STAGED")" == "$NEW" ]]',
        ):
            # The staged hash is checked as part of an expression.
            if fragment == '[[ "$(sha "$STAGED")" == "$NEW" ]]':
                self.assertIn('"$(sha "$STAGED")" == "$NEW"', self.text)
            else:
                self.assertIn(fragment, self.text)
        self.assertLess(self.text.index('install -m 0600 -o root -g root -- "$LIVE" "$BACK_LIB"'),
                        self.text.index('atomic_library "$STAGED" "$NEW"'))
        self.assertIn('atomic_library "$BACK_LIB" "$OLD"', self.text)
        self.assertIn('atomic_marker "$OLD"', self.text)

    def test_no_service_or_auth_modification(self):
        # It may inspect systemd but must not modify system services in this step.
        self.assertNotRegex(self.text, r"systemctl\s+(start|stop|restart|enable|disable|mask|unmask)\b")
        self.assertNotRegex(self.text, r"\bauthselect\s+(enable|disable|select|backup-restore)\b")
        self.assertNotIn("fprintd-delete", self.text)
        self.assertNotIn("fprintd-enroll", self.text)
        self.assertNotIn("FT5955_ALLOW_UNVERIFIED_ATTACH=", self.text)
        self.assertIn('mv -fT -- "$temporary" "$LIVE"', self.text)
        self.assertIn('mv -fT -- "$tmpmarker" "$MARK"', self.text)
        self.assertEqual(len(re.findall(r"\bchmod\s+0644\s+--", self.text)), 1)


if __name__ == "__main__":
    unittest.main()
