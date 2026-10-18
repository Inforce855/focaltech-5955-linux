#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Fail-closed read-only preflight for a separate MOH system-service install.

Does not create users, copy vendor DLLs, install units, touch the live
/run/ft5955-engine socket, enable fprintd/PAM or execute the matcher.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import pwd
import stat
import sys

SERVICE_USER = "ft5955-engine"
PROTECTED_ROOT = Path("/opt/ft5955-system-trial/engine")
PROTECTED_VENDOR = Path("/var/lib/ft5955-engine/vendor")
LIVE_SOCKET = Path("/run/ft5955-engine")
SYSTEMD_SERVICE = Path("/etc/systemd/system/ft5955-engine.service")
SYSTEMD_SOCKET = Path("/etc/systemd/system/ft5955-engine.socket")


def path_status(path: Path) -> str:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return "ABSENT"
    if stat.S_ISLNK(info.st_mode):
        return "SYMLINK (refuse)"
    kind = "DIRECTORY" if stat.S_ISDIR(info.st_mode) else "FILE" if stat.S_ISREG(info.st_mode) else "OTHER"
    return f"{kind} uid={info.st_uid} gid={info.st_gid} mode={stat.S_IMODE(info.st_mode):04o}"


def collect() -> tuple[list[tuple[str, str]], list[str]]:
    observations = []
    for path in (PROTECTED_ROOT, PROTECTED_VENDOR, LIVE_SOCKET, SYSTEMD_SERVICE, SYSTEMD_SOCKET):
        observations.append((str(path), path_status(path)))
    blockers = []
    try:
        service = pwd.getpwnam(SERVICE_USER)
        observations.append(("dedicated account", f"uid={service.pw_uid} shell={service.pw_shell}"))
        if service.pw_uid == 0:
            blockers.append("service account is root")
    except KeyError:
        observations.append(("dedicated account", "ABSENT"))
        blockers.append("dedicated service account not installed")
    # A previous user-owned trial socket must not be commandeered or replaced.
    live = path_status(LIVE_SOCKET)
    if live != "ABSENT":
        blockers.append("live MOH socket directory exists: preserve it; do not install over it")
    if path_status(PROTECTED_ROOT) == "ABSENT" or path_status(PROTECTED_VENDOR) == "ABSENT":
        blockers.append("protected engine/vendor installation not yet provisioned")
    for path in (PROTECTED_ROOT, PROTECTED_VENDOR):
        if path_status(path) != "ABSENT":
            from tools.audit_ft5955_auth_paths import audit_path
            blockers.extend(f"{path}: {issue}" for issue in audit_path(path, kind="dir"))
    blockers.append("privileged matcher/template integrity, ABI and sandbox not validated")
    blockers.append("PAM activation remains prohibited")
    return observations, blockers


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", action="store_true", help="show read-only installation blockers")
    parser.add_argument("--install", action="store_true", help="intentionally unsupported: fail closed")
    args = parser.parse_args()
    if args.install:
        print("REFUSED: protected MOH installer is not security-approved; no changes made")
        return 2
    if not args.plan:
        parser.error("only --plan is supported")
    observations, blockers = collect()
    for label, status in observations:
        print(f"{label}: {status}")
    for blocker in blockers:
        print(f"BLOCKER: {blocker}")
    print("READ-ONLY PASS: no system changes. AUTHENTICATION NOT APPROVED.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
