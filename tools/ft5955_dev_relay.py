#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Root fprintd stdio relay to the protected, SEPARATE MOH development socket.

Never loads Windows DLL or makes a match decision. No fallback to the older
user-owned trial broker. Intended only for the guarded no-PAM hardware trial.
"""
import importlib.util
import os
from pathlib import Path
import stat
import sys

BROKER=Path("/opt/ft5955-dev/ft5955_engine_broker.py")
SOCKET="/run/ft5955-engine-dev/engine.sock"

def main():
    if os.geteuid()!=0:
        raise RuntimeError("privileged fprintd relay requires UID 0")
    info=BROKER.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid!=0 or info.st_mode & 0o022:
        raise RuntimeError("untrusted relay module")
    spec=importlib.util.spec_from_file_location("ft5955_protected_relay",BROKER)
    if spec is None or spec.loader is None:
        raise RuntimeError("broker module unavailable")
    broker=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(broker)
    return broker.relay(SOCKET)

if __name__=="__main__":
    try:
        sys.exit(main())
    except (OSError,RuntimeError,ValueError):
        print("FT5955 isolated fprintd relay refused",file=sys.stderr)
        sys.exit(2)
