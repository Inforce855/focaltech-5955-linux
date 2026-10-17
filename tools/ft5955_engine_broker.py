#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Experimental non-root MOH broker / fprintd stdio relay.

NO live system integration yet. Do not configure PAM or turn on
FT5955_EXPERIMENTAL_ENABLE on the normal fprintd service with this alone.

Root fprintd would execute only this tiny relay (never the vendor engine).
The broker must run in a separate non-root systemd service, listening on a
protected AF_UNIX socket provided as fd 3 by systemd socket activation.
Only peer UID 0 (fprintd) is accepted in production. One MOH gateway process
is created per connection; raw samples and templates are never logged.
--test-only permits a local non-root synthetic protocol test; root cannot use it.
"""
from __future__ import annotations

import argparse
import os
import pwd
import select
from pathlib import Path
import signal
import socket
import stat
import struct
import subprocess
import sys
import threading
import time

SOCKET_PATH = "/run/ft5955-engine/engine.sock"
SESSION_LIMIT = 240
CHUNK = 8192


def copy_stream(reader, writer, *, socket_writer=False):
    """Pipes already deliver bounded chunks; no accumulated biometric buffer."""
    try:
        while True:
            data = reader(CHUNK)
            if not data:
                break
            writer(data)
    except (OSError, ValueError, BrokenPipeError, ConnectionError):
        pass
    finally:
        if socket_writer:
            try:
                socket_writer.shutdown(socket.SHUT_WR)
            except OSError:
                pass


def write_stdout_all(data: bytes) -> None:
    view = memoryview(data)
    while view:
        written = os.write(1, view)
        if written <= 0:
            raise BrokenPipeError("Unable to forward gateway reply")
        view = view[written:]


def relay(path: str) -> int:
    """Run as the system fprintd's transient child. Never load vendor code."""
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as remote:
        remote.settimeout(SESSION_LIMIT)
        remote.connect(path)
        up = threading.Thread(
            target=copy_stream,
            args=(lambda n: os.read(0, n), remote.sendall),
            kwargs={"socket_writer": remote},
            daemon=True,
        )
        up.start()
        copy_stream(remote.recv, write_stdout_all)
        # Never keep the service running after the client has finished.
    up.join(timeout=1)
    return 0


def authorized_client(conn: socket.socket, *, test_only: bool) -> bool:
    cred = conn.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12)
    _pid, uid, _gid = struct.unpack("3i", cred)
    return uid == (os.geteuid() if test_only else 0)


def clean_environment() -> dict[str, str]:
    # A fresh, dedicated engine account must be able to resolve its own home.
    # No caller-provided LD_PRELOAD, Python search paths or FT5955 modes.
    return {
        "PATH": "/usr/sbin:/usr/bin:/sbin:/bin",
        "HOME": pwd.getpwuid(os.geteuid()).pw_dir,
        "LANG": "C",
    }


def serve_session(conn: socket.socket, gateway: Path, moh_dir: Path) -> None:
    conn.settimeout(SESSION_LIMIT)
    # Vendor code is NEVER executed as root; see serve().
    child = subprocess.Popen(
        ["/usr/bin/python3", str(gateway), "--moh-dir", str(moh_dir)],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL, cwd="/", env=clean_environment(),
        start_new_session=True, bufsize=0,
    )
    assert child.stdin is not None and child.stdout is not None
    started = time.monotonic()

    def toward_gateway():
        try:
            copy_stream(conn.recv, child.stdin.write)
        finally:
            try:
                child.stdin.close()
            except OSError:
                pass

    inbound = threading.Thread(target=toward_gateway, daemon=True)
    inbound.start()

    def bounded_gateway_read(n: int) -> bytes:
        remaining = SESSION_LIMIT - (time.monotonic() - started)
        if remaining <= 0 or not select.select([child.stdout], [], [], remaining)[0]:
            raise TimeoutError("Gateway exceeded bounded session")
        return os.read(child.stdout.fileno(), n)

    try:
        copy_stream(bounded_gateway_read, conn.sendall, socket_writer=conn)
    finally:
        if child.poll() is None:
            # If peer died/cancelled, terminate the complete engine group.
            try:
                os.killpg(child.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                child.wait(timeout=3)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                child.wait(timeout=3)
        else:
            child.wait(timeout=3)
        try:
            child.stdout.close()
        except OSError:
            pass
        if time.monotonic() - started > SESSION_LIMIT:
            print("FT5955 broker session exceeded time limit", file=sys.stderr)


def check_owned_gateway(gateway: Path, moh_dir: Path, test_only: bool) -> None:
    if not gateway.is_absolute() or not gateway.is_file() or gateway.is_symlink():
        raise ValueError("Gateway must be an existing absolute regular file")
    if not moh_dir.is_absolute() or not moh_dir.is_dir() or moh_dir.is_symlink():
        raise ValueError("MOH path must be an existing absolute directory")
    if not test_only:
        st = gateway.stat()
        if st.st_uid != 0 or st.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
            raise ValueError("The gateway must be root-owned and not group/world writable")
        # The actual audited MOH runner and DLL belong in a separate protected
        # directory. The server never reads a user's home directory directly.


def serve(args) -> int:
    if os.geteuid() == 0:
        raise ValueError("Broker MUST run as a dedicated non-root account")
    gateway = Path(args.gateway)
    moh_dir = Path(args.moh_dir)
    check_owned_gateway(gateway, moh_dir, args.test_only)

    if args.test_only:
        directory = Path(args.socket).parent
        if not directory.is_dir() or directory.stat().st_uid != os.geteuid():
            raise ValueError("Synthetic socket parent must be owned by test UID")
        listening = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        listening.bind(args.socket)
        os.chmod(args.socket, 0o600)
        listening.listen(1)
    else:
        if args.socket != SOCKET_PATH:
            raise ValueError("Only the fixed system socket is permitted")
        if os.getenv("LISTEN_PID") != str(os.getpid()) or os.getenv("LISTEN_FDS") != "1":
            raise ValueError("Requires one systemd-activated socket (fd 3)")
        listening = socket.socket(fileno=3)
        if listening.family != socket.AF_UNIX or listening.getsockopt(socket.SOL_SOCKET, socket.SO_ACCEPTCONN) != 1:
            raise ValueError("fd 3 is not a listening AF_UNIX socket")

    with listening:
        while True:
            conn, _ = listening.accept()
            with conn:
                if not authorized_client(conn, test_only=args.test_only):
                    print("FT5955 broker refused unauthorized peer", file=sys.stderr)
                    continue
                try:
                    serve_session(conn, gateway, moh_dir)
                except (OSError, ValueError, subprocess.SubprocessError) as exc:
                    # Do not print potentially sensitive inputs or templates.
                    print("FT5955 broker session error: " + type(exc).__name__, file=sys.stderr)
            if args.test_only:
                break
    if args.test_only:
        Path(args.socket).unlink(missing_ok=True)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--test-only", action="store_true")
    parser.add_argument("--socket", default=SOCKET_PATH)
    parser.add_argument("--gateway")
    parser.add_argument("--moh-dir")
    args = parser.parse_args()

    if args.test_only and os.geteuid() == 0:
        raise ValueError("--test-only cannot run as root")
    if args.serve:
        if not args.gateway or not args.moh_dir:
            parser.error("--serve needs --gateway and --moh-dir")
        return serve(args)
    if args.gateway or args.moh_dir:
        parser.error("--gateway/--moh-dir are only valid in --serve mode")
    if not args.test_only and args.socket != SOCKET_PATH:
        raise ValueError("Production relay must use the fixed system socket")
    if not args.test_only and os.geteuid() != 0:
        raise ValueError("Production relay must be launched by root-owned fprintd")
    return relay(args.socket)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print("FT5955 broker/relay stopped: " + type(exc).__name__, file=sys.stderr)
        sys.exit(2)
