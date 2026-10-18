#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""DEV ONLY: socket-activated MOH startup probe. No fingerprint authentication.

Runs the audited MOH ELF inside bwrap as the service account, with no frame
or template input. Exposes only an explicit negative result to root peers.
Never forwards MATCH or biometric data. Intended for separate -dev socket.
"""
import os
import socket
import struct
import subprocess
import sys

SOCKET="/run/ft5955-engine-dev/engine.sock"
ELF="/opt/ft5955-dev/live-identify"
DLL="/usr/local/lib/focaltech-5955/ftWbioEngineAdapter.dll"
EXPECTED_UID=955

def startup():
    command=[
        "/usr/bin/timeout","--signal=TERM","--kill-after=3s","15s",
        "/usr/bin/bwrap","--unshare-all","--die-with-parent","--new-session",
        "--clearenv","--ro-bind","/usr","/usr",
        "--symlink","usr/lib64","/lib64",
        "--proc","/proc","--dev","/dev","--tmpfs","/tmp",
        "--ro-bind",ELF,"/tmp/live-identify",
        "--ro-bind",DLL,"/tmp/engine.dll",
        "--chdir","/tmp","--","/tmp/live-identify",
        "--live-identify","/tmp/engine.dll"
    ]
    # Discard vendor output: neither logs nor socket must disclose biometric data.
    result=subprocess.run(command,input=b"",stdout=subprocess.DEVNULL,
                          stderr=subprocess.PIPE,timeout=21,check=False)
    # Emit only a fixed-category failure code; never forward vendor logs,
    # samples, paths or subprocess stderr to the journal or the socket.
    if result.returncode != 0:
        stderr=result.stderr or b""
        category=("NAMESPACE_DENIED" if b"Creating new namespace failed" in stderr or b"Operation not permitted" in stderr else
                  "EXEC_PATH" if b"No such file or directory" in stderr else
                  "TIMEOUT" if result.returncode in (124,137) else "OTHER")
        print(f"FT5955_DEV_STARTUP_FAILED category={category} exit={result.returncode}",file=sys.stderr,flush=True)
    return result.returncode==0

def main():
    if os.geteuid()!=EXPECTED_UID:
        raise RuntimeError("dev service must run under dedicated UID 955")
    if os.environ.get("LISTEN_PID")!=str(os.getpid()) or os.environ.get("LISTEN_FDS")!="1":
        raise RuntimeError("requires single systemd socket")
    listener=socket.socket(fileno=3)
    if listener.family!=socket.AF_UNIX or listener.getsockopt(socket.SOL_SOCKET,socket.SO_ACCEPTCONN)!=1:
        raise RuntimeError("unexpected socket")
    while True:
        client,_=listener.accept()
        with client:
            _pid,uid,_gid=struct.unpack("3i",client.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
            if uid!=0:
                continue
            try:
                result=startup()
            except (OSError,subprocess.TimeoutExpired):
                result=False
            # Always fail closed: even successful startup is not authentication.
            client.sendall(b"ERROR DEV_MOH_STARTED_NO_AUTH\n" if result else b"ERROR DEV_MOH_START_FAILED_NO_AUTH\n")

if __name__=="__main__":
    try:main()
    except (OSError,RuntimeError) as exc:
        print("FT5955 dev startup server refused: "+type(exc).__name__,file=sys.stderr)
        sys.exit(2)
