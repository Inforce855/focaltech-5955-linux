#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Development-only systemd socket server. Never emits MATCH or templates."""
import os
import socket
import struct
import sys

def main():
    if os.geteuid() == 0:
        raise RuntimeError("refuse root")
    if os.environ.get("LISTEN_PID") != str(os.getpid()) or os.environ.get("LISTEN_FDS") != "1":
        raise RuntimeError("requires exactly one systemd-activated socket")
    listener = socket.socket(fileno=3)
    if listener.family != socket.AF_UNIX or not listener.getsockopt(socket.SOL_SOCKET, socket.SO_ACCEPTCONN):
        raise RuntimeError("invalid listener")
    while True:
        peer, _ = listener.accept()
        with peer:
            _, uid, _ = struct.unpack("3i", peer.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
            if uid != 0:
                continue
            # No biometric protocol accepted. A root-side client can check
            # reachability but no operation may produce authentication success.
            peer.sendall(b"ERROR DEV_ONLY_NO_AUTH\n")

if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError) as exc:
        print("FT5955 DEV service refused: " + type(exc).__name__, file=sys.stderr)
        sys.exit(2)
