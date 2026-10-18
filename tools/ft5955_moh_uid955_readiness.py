#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Read-only service-account readiness audit for a future real MOH runner.

No DLL execution, fingerprint frames, system modifications, or PAM changes.
Run without sudo; an optional dedicated service-account probe runs only on
files already designated for system service use.
"""
from __future__ import annotations
import argparse
import os
from pathlib import Path
import pwd
import stat
import sys

NEEDED = ("tools/test_moh_isolated_live_identify.sh",
          "tools/moh_engine_preflight.py", "engine/ft_engine.c")
SERVICE = "ft5955-engine"

def examine(root: Path, dll: Path):
    problems = []
    try:
        account = pwd.getpwnam(SERVICE)
        print(f"SERVICE ACCOUNT: uid={account.pw_uid}, shell={account.pw_shell}")
        if account.pw_uid in (0, os.getuid()):
            problems.append("service UID must differ from root and login user")
    except KeyError:
        problems.append("service account not installed")
    for label, path in [("proposed MOH root", root), ("pinned DLL", dll)] + [
        (p, root/p) for p in NEEDED
    ]:
        try:
            info = path.lstat()
            kind = "directory" if stat.S_ISDIR(info.st_mode) else "file" if stat.S_ISREG(info.st_mode) else "other"
            unsafe = stat.S_ISLNK(info.st_mode) or info.st_uid != 0 or bool(info.st_mode & 0o022)
            print(f"{label}: {kind} uid={info.st_uid} mode={stat.S_IMODE(info.st_mode):04o}" +
                  (" [NOT TRUSTED]" if unsafe else ""))
            if unsafe:
                problems.append(f"{label}: untrusted ownership/type/permissions")
        except OSError as exc:
            print(f"{label}: MISSING ({type(exc).__name__})")
            problems.append(f"{label}: unavailable")
    print("NO execution or installation performed.")
    if problems:
        for p in problems:
            print(f"BLOCKER: {p}")
    print("RESULT:", "NOT READY" if problems else "FILE METADATA ONLY PASS — runtime unverified")
    print("PRODUCTION AUTHENTICATION NOT APPROVED")
    return int(bool(problems))

def main():
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument("--moh-root",type=Path,default=Path("/var/lib/ft5955-engine/vendor"))
    a.add_argument("--dll",type=Path,default=Path("/usr/local/lib/focaltech-5955/ftWbioEngineAdapter.dll"))
    v=a.parse_args()
    if os.geteuid()==0:
        a.error("run read-only as normal user, never sudo")
    return examine(v.moh_root,v.dll)

if __name__=="__main__":
    sys.exit(main())
