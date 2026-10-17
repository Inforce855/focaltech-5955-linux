#!/usr/bin/env python3
"""Inspect or safely export the local pinned libfprint scaffold commit delta.

By default performs READ-ONLY inspection. --export requires an absolute,
nonexistent output path OUTSIDE the live checkout. Never fetches remotes,
modifies Git, installs, scans fingerprints, invokes fprintd or enrolls.
"""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import subprocess
import sys

BASE = "c8e01dc26cedb2d97779a314a7260f1c33e02bfa"
PARENT = "68696e04a88efbecd5dd79cebf05b8ef013c51d8"
ALLOWED = frozenset((
    "meson.build",
    "libfprint/meson.build",
    "libfprint/drivers/focaltech_5955.c",
))
LIMIT = 200_000


def git(root: Path, *args: str) -> bytes:
    return subprocess.check_output(
        ["git", "-C", str(root), *args],
        stderr=subprocess.PIPE, timeout=20,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--libfprint", default="~/Projects/libfprint-ft5955",
                        help="Existing Git checkout; read-only, worktree not modified")
    parser.add_argument("--export", metavar="ABSOLUTE_PATCH_PATH",
                        help="Optional explicit reviewable patch file, outside live checkout")
    args = parser.parse_args()
    if os.geteuid() == 0:
        raise ValueError("Run as a normal user, never root")
    root = Path(args.libfprint).expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"Missing libfprint Git checkout: {root}")
    gitroot = git(root, "rev-parse", "--show-toplevel").decode().strip()
    if Path(gitroot).resolve() != root:
        raise ValueError("The --libfprint path must be the Git worktree root")
    for sha in (BASE, PARENT):
        if git(root, "cat-file", "-t", sha).strip() != b"commit":
            raise ValueError(f"Required commit not present: {sha}")
    actual = git(root, "rev-list", "--parents", "-n", "1", BASE).decode().split()
    if actual != [BASE, PARENT]:
        raise ValueError("Unexpected ancestry; do not reconstruct from this checkout")

    data = git(root, "diff", "--no-ext-diff", "--no-textconv", "--no-renames",
               "--name-status", "-z", PARENT, BASE)
    parts = data.split(b"\0")
    if not parts or parts[-1] != b"":
        raise ValueError("Unexpected Git diff name-status encoding")
    parts.pop()
    if len(parts) % 2:
        raise ValueError("Unexpected Git diff name-status record")
    entries = []
    for i in range(0, len(parts), 2):
        status = parts[i].decode("ascii")
        name = parts[i + 1].decode("utf-8")
        entries.append((status, name))

    print("BASE:", BASE)
    print("PARENT:", PARENT)
    print("CHANGED_FILE_COUNT:", len(entries))
    for status, name in entries:
        print(" ", status, name)

    # Explicitly refuse to silently discard other changes made in the
    # local base commit; no patch is exported until the whole delta is known.
    unexpected = [(s, p) for s, p in entries
                  if p not in ALLOWED or s not in ("A", "M")]
    if unexpected or not entries:
        raise ValueError(
            "Base contains unexpected or no file changes; REVIEW REQUIRED, "
            "no patch exported")

    for _, name in entries:
        # Avoid publishing symbolic links, executables, etc. unknowingly.
        mode_line = git(root, "ls-tree", BASE, "--", name).decode().strip()
        if not mode_line.startswith("100644 blob "):
            raise ValueError(f"Unexpected file mode for {name}; review before export")

    patch = git(root, "diff", "--no-ext-diff", "--no-textconv", "--no-renames",
                "--binary", PARENT, BASE, "--", *sorted(ALLOWED))
    if not patch.startswith(b"diff --git ") or len(patch) > LIMIT:
        raise ValueError("Scaffold patch empty, oversized or not a Git patch")
    if b"GIT binary patch" in patch or b"\0" in patch:
        raise ValueError("Binary patch is not permitted")
    patch.decode("utf-8")
    print("SCAFFOLD_PATCH_BYTES:", len(patch))
    print("SCAFFOLD_PATCH_SHA256:", hashlib.sha256(patch).hexdigest())
    print("PASS: exact pinned parent-to-base source delta inspected; no files modified.")
    print("UPSTREAM_AVAILABILITY: NOT VERIFIED (local Git objects only)")

    if args.export is None:
        print("READ ONLY: to preserve reviewed patch later, use --export /tmp/name.patch")
        return
    dest = Path(args.export).expanduser()
    if not dest.is_absolute():
        raise ValueError("--export must be an absolute file path")
    dest = dest.absolute()
    if dest.is_relative_to(root) or dest.is_relative_to(Path.home() / "Projects" / "ft5955-driver-consolidated"):
        raise ValueError("Refusing to export inside either live or consolidated source tree")
    if dest.exists() or dest.is_symlink() or not dest.parent.is_dir():
        raise ValueError("Destination already exists, is a symlink, or parent directory missing")
    fd = os.open(dest, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(patch)
    print("EXPORTED:", str(dest))
    print("REVIEW before committing the patch to any public repository.")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError,
            subprocess.TimeoutExpired, UnicodeError) as exc:
        sys.exit(f"SCAFFOLD INSPECTION STOPPED: {exc}")
