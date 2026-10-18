#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""DEV: socket-activated real MOH protocol server (separate from live socket).

Accepts only kernel-credentialled UID 0, then delegates a single bounded
MODE/FRAME transaction to the already-tested AF_UNIX broker's session relay.
The proprietary DLL executes only inside the UID955 bubblewrap child.
No fprintd, KDE, PAM, or enrolment storage is changed by this program.
"""
import importlib.util
import os
from pathlib import Path
import pwd
import stat
import sys
from types import SimpleNamespace

ROOT=Path("/opt/ft5955-dev")
BROKER=ROOT/"ft5955_engine_broker.py"
GATEWAY=ROOT/"ft5955_dev_template_gateway.py"
SOCKET="/run/ft5955-engine-dev/engine.sock"

def main():
    if os.geteuid()!=pwd.getpwnam("ft5955-engine").pw_uid or os.geteuid()==0:
        raise RuntimeError("not dedicated non-root engine service")
    for p in (BROKER,GATEWAY):
        st=p.lstat()
        if not stat.S_ISREG(st.st_mode) or st.st_uid!=0 or st.st_mode & 0o022:
            raise RuntimeError("untrusted broker or gateway")
    spec=importlib.util.spec_from_file_location("ft5955_protected_broker",BROKER)
    if spec is None or spec.loader is None:
        raise RuntimeError("broker cannot be loaded")
    broker=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(broker)
    broker.SOCKET_PATH=SOCKET
    args=SimpleNamespace(
        serve=True,test_only=False,serve_user_trial=False,
        socket=SOCKET,gateway=str(GATEWAY),moh_dir=str(ROOT)
    )
    return broker.serve(args)

if __name__=="__main__":
    try:
        sys.exit(main())
    except (OSError,ValueError,RuntimeError,KeyError):
        print("FT5955 development protocol service refused to start",file=sys.stderr)
        sys.exit(2)
