#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""DEV: run the prebuilt MOH template protocol inside the proven UID955 sandbox.

This program is exclusively the subprocess transport for engine_gateway.py.
It never reads biometric frames itself and never makes an authorization decision.
Do not enable PAM until service-owned templates and vendor-engine risks are reviewed.
"""
import ast
import hashlib
import os
from pathlib import Path
import pwd
import stat
import sys

ROOT=Path("/opt/ft5955-dev")
EXE=ROOT/"live-template"
DLL=Path("/usr/local/lib/focaltech-5955/ftWbioEngineAdapter.dll")
PREFLIGHT=ROOT/"real-moh-source/tools/moh_engine_preflight.py"
UID_NAME="ft5955-engine"

def trusted(path: Path) -> None:
    info=path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid!=0 or info.st_mode & 0o022:
        raise RuntimeError("untrusted protected runtime file")

def dll_pin() -> str:
    trusted(PREFLIGHT)
    tree=ast.parse(PREFLIGHT.read_text(encoding="utf-8"))
    values=[n.value.value for node in tree.body if isinstance(node,ast.Assign)
            for n in node.targets if isinstance(n,ast.Name) and n.id=="PIN"
            if isinstance(node.value,ast.Constant) and isinstance(node.value.value,str)]
    if len(values)!=1 or len(values[0])!=64 or any(x not in "0123456789abcdefABCDEF" for x in values[0]):
        raise RuntimeError("missing pinned Windows DLL digest")
    return values[0].lower()

def main():
    if os.geteuid()!=pwd.getpwnam(UID_NAME).pw_uid or os.geteuid()==0:
        raise RuntimeError("wrong dedicated service account")
    for path in (ROOT, ROOT/"real-moh-source", EXE.parent, DLL.parent):
        info=path.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid!=0 or info.st_mode & 0o022:
            raise RuntimeError("untrusted protected runtime directory")
    for path in (EXE,DLL):
        trusted(path)
    with DLL.open("rb") as inp:
        digest=hashlib.file_digest(inp,"sha256").hexdigest()
    if digest!=dll_pin():
        raise RuntimeError("Windows DLL SHA-256 audit mismatch")
    # Preserve the working nested sandbox arrangement: no writable host files,
    # USB devices, network, or user home visible to the proprietary engine.
    # The inherited host /proc read-only bind is a known DEV security limitation.
    command=[
        "/usr/bin/timeout","--signal=TERM","--kill-after=3s","195s",
        "/usr/bin/bwrap","--unshare-all","--die-with-parent","--new-session",
        "--clearenv","--ro-bind","/usr","/usr",
        "--symlink","usr/lib64","/lib64",
        "--ro-bind","/proc","/proc","--dev","/dev","--tmpfs","/tmp",
        "--ro-bind",str(EXE),"/tmp/live-template",
        "--ro-bind",str(DLL),"/tmp/engine.dll",
        "--chdir","/tmp","--","/tmp/live-template",
        "--live-identify","/tmp/engine.dll"
    ]
    os.execv(command[0],command)

if __name__=="__main__":
    try:
        main()
    except (OSError,ValueError,RuntimeError,KeyError,SyntaxError):
        # Do not emit the vendor DLL's content or any fingerprint material.
        print("FT5955 protected template runner preflight failed",file=sys.stderr)
        sys.exit(2)
