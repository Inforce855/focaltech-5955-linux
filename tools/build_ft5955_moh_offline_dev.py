#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Offline reproduction of the MOH C build using the protected dev source.

Compiles only. Does not execute generated binary, vendor DLL, bwrap, PAM,
fprintd, or engine. Build output is a caller-owned temporary directory.
"""
import argparse
from pathlib import Path
import os
import re
import shlex
import subprocess
import sys

ROOT=Path("/opt/ft5955-dev/real-moh-source")
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--output-dir",type=Path,required=True)
    args=ap.parse_args()
    if os.geteuid()==0:
        ap.error("do not run compiler wrapper as root")
    runner=ROOT/"tools/test_moh_isolated_live_identify.sh"
    if not runner.is_file() or runner.is_symlink():
        ap.error("protected MOH runner missing")
    out=args.output_dir.resolve()
    if not out.is_dir() or out.is_symlink() or out.stat().st_uid!=os.geteuid():
        ap.error("output directory must exist and be owned by caller")
    if out == ROOT or ROOT in out.parents:
        ap.error("build output must not be inside protected source")
    data=runner.read_text()
    match=re.search(r"(?m)^gcc [^\n]*(?:\\\n[^\n]*)*",data)
    if not match:
        ap.error("GCC command not found")
    command=match.group().replace("\\\n"," ")
    argv=shlex.split(command)
    if argv[0]!="gcc" or "-o" not in argv:
        ap.error("unrecognised command")
    idx=argv.index("-o")
    if idx+2!=len(argv) or argv[idx+1]!="$root/live-identify":
        ap.error("unexpected output directive")
    source=[x for x in argv if x.endswith(".c")]
    if len(source)!=21 or not all(re.fullmatch(r"(engine|tools)/[A-Za-z0-9_.-]+\.c",x) for x in source):
        ap.error("unexpected source list")
    for path in source:
        p=ROOT/path
        if not p.is_file() or p.is_symlink():
            ap.error("missing or unsafe build input "+path)
    argv[idx+1]=str(out/"live-identify")
    print(f"Compiling {len(source)} C files; original developer flags preserved.",flush=True)
    result=subprocess.run(argv,cwd=ROOT,check=False)
    if result.returncode:
        print(f"FAIL: GCC exited {result.returncode}")
        return result.returncode
    p=out/"live-identify"
    if not p.is_file():
        print("FAIL: output missing")
        return 1
    p.chmod(0o500)
    print(f"PASS: offline MOH C compile: {p}")
    print("Executable NOT RUN; no DLL/bwrap/PAM/fprintd operation.")
    print("NOT security-approved for live authentication.")
    return 0
if __name__=="__main__":
    sys.exit(main())
