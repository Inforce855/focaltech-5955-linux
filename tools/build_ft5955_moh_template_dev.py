#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build the real MOH enrol/verify protocol from protected source.

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
    # Follow shell line continuations explicitly; the previous regex stopped
    # after a trailing backslash and shlex raised 'No escaped character'.
    lines=runner.read_text().splitlines()
    first=next((i for i,line in enumerate(lines) if line.startswith("gcc ")),None)
    if first is None:
        ap.error("GCC command not found")
    parts=[]
    for line in lines[first:]:
        stripped=line.rstrip()
        continuation=stripped.endswith(chr(92))
        parts.append(stripped[:-1] if continuation else stripped)
        if not continuation:
            break
    else:
        ap.error("unfinished GCC line continuation")
    command=" ".join(parts)
    try:
        argv=shlex.split(command)
    except ValueError as exc:
        ap.error("invalid GCC shell syntax: "+str(exc))
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
    # Compile the audited engine, replacing only the C protocol frontend.
    original="tools/moh_engine_live_identify.c"
    replacement="tools/ft5955_template_session.c"
    if source.count(original)!=1 or not (ROOT/replacement).is_file() or (ROOT/replacement).is_symlink():
        ap.error("original frontend or protected template session source missing")
    argv=[replacement if token==original else token for token in argv]
    argv[idx+1]=str(out/"live-template")
    print(f"Compiling {len(source)} C files with audited flags and template frontend.",flush=True)
    result=subprocess.run(argv,cwd=ROOT,check=False)
    if result.returncode:
        print(f"FAIL: GCC exited {result.returncode}")
        return result.returncode
    p=out/"live-template"
    if not p.is_file():
        print("FAIL: output missing")
        return 1
    p.chmod(0o500)
    print(f"PASS: MOH enrol/verify protocol compile: {p}")
    print("Executable NOT RUN; no DLL/bwrap/PAM/fprintd operation.")
    print("DEV ONLY: no PAM integration or authentication approval.")
    return 0
if __name__=="__main__":
    sys.exit(main())
