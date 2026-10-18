#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Probe the independent synthetic MOH socket without biometric data."""
import argparse
import os
import socket
import sys

SOCKET = "/run/ft5955-engine-dev/engine.sock"

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--socket", default=SOCKET)
    a = p.parse_args()
    if a.socket != SOCKET:
        p.error("Only the independent dev socket is supported")
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.settimeout(3.0)
        try:
            s.connect(a.socket)
        except PermissionError:
            if os.geteuid() != 0:
                print("PASS: non-root client denied by socket permissions")
                return 0
            print("FAIL: root client unexpectedly denied")
            return 1
        try:
            reply = s.recv(256)
        except ConnectionResetError:
            reply = b""
    if os.geteuid() == 0:
        expected = b"ERROR DEV_ONLY_NO_AUTH\n"
        if reply != expected:
            print("FAIL: root-client expected fail-closed marker; received another result")
            return 1
        print("PASS: root client received explicit DEV_ONLY_NO_AUTH rejection")
    else:
        if reply:
            print("FAIL: non-root client received data")
            return 1
        print("PASS: non-root client rejected without authentication response")
    return 0

if __name__ == "__main__":
    sys.exit(main())
