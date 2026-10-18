#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Read-only audit of staged MOH source and runner dependencies.

Does not execute code, DLL, bwrap, fprintd, PAM or fingerprint capture.
"""
from pathlib import Path
import hashlib
import os
import pwd
import stat
import sys

STAGED=Path("/opt/ft5955-dev/real-moh-source")
FILES=("tools/test_moh_isolated_live_identify.sh",
       "tools/moh_engine_preflight.py", "engine/ft_engine.c")
def digest(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for data in iter(lambda:f.read(65536), b""):
            h.update(data)
    return h.hexdigest()
def main():
    if os.geteuid()==0:
        print("REFUSE: run as ordinary user, not sudo");return 2
    original=Path.home()/"Projects/focaltech-5955-moh-test"
    blockers=[]
    for rel in FILES:
        a,b=original/rel,STAGED/rel
        if not a.is_file() or not b.is_file() or a.is_symlink() or b.is_symlink():
            print(f"FAIL {rel}: missing/nonregular/symlink");blockers.append(rel);continue
        s=b.lstat()
        ok=s.st_uid==0 and not(s.st_mode & 0o022) and digest(a)==digest(b)
        print(f"{'PASS' if ok else 'FAIL'} {rel}: staged sha256={digest(b)} uid={s.st_uid} mode={stat.S_IMODE(s.st_mode):04o}")
        if not ok: blockers.append(rel)
    manifest=STAGED/"SHA256SUMS"
    if not manifest.is_file() or manifest.is_symlink():
        blockers.append("SHA256SUMS")
    else:
        for rel in FILES:
            if rel not in manifest.read_text():
                blockers.append("manifest missing "+rel)
    print("=== Runtime source dependency inventory (no execution) ===")
    source=original/"tools/test_moh_isolated_live_identify.sh"
    if source.is_file():
        for n,line in enumerate(source.read_text(errors="replace").splitlines(),1):
            if any(tok in line for tok in ("gcc ","-I","-l","python3","moh_engine_preflight","bwrap","--ro-bind","-DFT5955_","ft_engine.c")):
                print(f"runner line {n}: {line[:240]}")
    for rel in ("engine/ft_engine.c","tools/moh_engine_preflight.py"):
        p=original/rel
        if p.is_file():
            for n,line in enumerate(p.read_text(errors="replace").splitlines(),1):
                if line.lstrip().startswith(("#include","import ","from ")):
                    print(f"{rel}:{n} {line[:180]}")
    print("RESULT:", "FAIL — SOURCE MISMATCH" if blockers else "PASS — 3 SOURCE COPIES MATCH (not runtime approval)")
    print("NOT AUTHORISED FOR PAM: remaining dependencies, sandbox and engine ABI require review.")
    return int(bool(blockers))
if __name__=="__main__":
    sys.exit(main())
