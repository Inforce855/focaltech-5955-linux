#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Read-only MOH launcher relocation/security audit for Nobara Linux.

This tool intentionally does NOT execute the DLL, sandbox, loader, runner,
fprintd, USB or any fingerprint actions. It checks only existing paths,
file ownership, static wrapper structure and pinned SHA-256 digest.
It never prints biometric data, private DLL bytes or file content.
Run only as normal user; no installation or privilege escalation.
"""
from __future__ import annotations

import ast
import hashlib
import os
from pathlib import Path
import pwd
import re
import shutil
import stat
import subprocess
import sys


MOH_ROOT = Path.home() / "Projects" / "focaltech-5955-moh-test"
RUNNER = MOH_ROOT / "tools" / "test_moh_isolated_live_identify.sh"
DLL = Path("/usr/local/lib/focaltech-5955/ftWbioEngineAdapter.dll")
PREFLIGHT = MOH_ROOT / "tools" / "moh_engine_preflight.py"
CRITICAL_SOURCE = MOH_ROOT / "engine" / "ft_engine.c"
CHECKS = ["bwrap", "gcc", "python3", "objdump", "timeout"]


def flag(label: str, ok: bool, detail: str = "") -> None:
    print(f"{'PASS' if ok else 'BLOCKER'}: {label}{': ' + detail if detail else ''}")


def pinned_sha256(source: str) -> str | None:
    """Read a literal PIN assignment, never evaluate/import untrusted code."""
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        return None
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for item in node.targets:
                if isinstance(item, ast.Name) and item.id == "PIN":
                    if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                        if re.fullmatch(r"[0-9a-fA-F]{64}", node.value.value):
                            return node.value.value.lower()
    return None


def is_regular_nonsymlink(path: Path) -> bool:
    try:
        info = path.lstat()
        return stat.S_ISREG(info.st_mode)
    except OSError:
        return False


def main() -> int:
    if os.geteuid() == 0:
        print("STOP: never run this audit as root / sudo.", file=sys.stderr)
        return 2
    print("=== FT5955 MOH RELOCATION AUDIT — READ ONLY / NO FINGERPRINTS ===")
    blockers = []
    for path, desc in (
        (RUNNER, "Audited launcher source"),
        (PREFLIGHT, "110-import / SHA preflight module"),
        (CRITICAL_SOURCE, "MOH engine C source"),
        (DLL, "Pinned vendor DLL at established default path"),
    ):
        ok = is_regular_nonsymlink(path)
        flag(desc, ok)
        if not ok:
            blockers.append(desc)

    missing = [cmd for cmd in CHECKS if shutil.which(cmd) is None]
    flag("Existing audit/sandbox commands available", not missing,
         ", ".join(missing) if missing else "all found")
    if missing:
        blockers.append("required external commands")

    if RUNNER.is_file():
        check = subprocess.run(
            ["bash", "-n", str(RUNNER)], check=False, capture_output=True, timeout=6
        )
        flag("Existing runner bash syntax", check.returncode == 0)
        if check.returncode != 0:
            blockers.append("shell syntax")
        text = RUNNER.read_text(encoding="utf-8")
        guards = (
            'set -euo pipefail',
            'cd "$(dirname "$0")/.."',
            'import tools.moh_engine_preflight as p',
            'p.archive_engine(',
            'p.audit(',
            'hashlib.file_digest(',
            '--unshare-all',
            '--die-with-parent',
            '--clearenv',
            '--tmpfs /tmp',
            'timeout --signal=KILL 1200s bwrap',
        )
        ok = all(g in text for g in guards)
        flag("Known, protected original runner layout", ok)
        if not ok:
            blockers.append("runner content changed since reviewed source")
        print("INFO: launcher relies on the MOH source-tree cwd for C files/imports.")
        print("INFO: unmodified launcher defaults to /usr/local/lib/focaltech-5955.")
        print("INFO: original runner accepts a positional installed DLL path.")
        if "-DFT5955_ALLOW_UNVERIFIED_ATTACH" in text:
            print("SECURITY REVIEW REQUIRED: runner enables UNVERIFIED_ATTACH.")
            print("This diagnostic permission is not production-login approval.")

    if DLL.exists():
        info = DLL.stat()
        ok = info.st_uid == 0 and not (info.st_mode & (stat.S_IWGRP | stat.S_IWOTH))
        flag("Installed vendor DLL is root-owned and not group/world writable", ok)
        if not ok:
            blockers.append("DLL ownership / write permissions")

    if DLL.is_file() and PREFLIGHT.is_file():
        pin = pinned_sha256(PREFLIGHT.read_text(encoding="utf-8"))
        if pin is None:
            flag("Pinned digest statically located", False,
                 "PIN is not a simple SHA256 string assignment; inspect manually")
            blockers.append("pin extraction")
        else:
            h = hashlib.sha256()
            with DLL.open("rb") as fd:
                for block in iter(lambda: fd.read(65536), b""):
                    h.update(block)
            ok = h.hexdigest() == pin
            flag("Installed vendor DLL matches audit pin (SHA-256)", ok)
            if not ok:
                blockers.append("DLL digest mismatch")

    print("INFO: no DLL, runner, bwrap or fingerprint operation was executed.")
    print("INFO: systemd non-root service still requires separate isolated testing.")
    if blockers:
        print("RESULT: relocation prerequisites have BLOCKERS (no files changed).")
        return 1
    print("RESULT: local inputs verified; production/login security NOT established.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, UnicodeError, subprocess.TimeoutExpired) as exc:
        print("ERROR: audit failed: " + type(exc).__name__, file=sys.stderr)
        sys.exit(2)
