#!/usr/bin/env python3
"""Read-only audit of pinned libfprint base Git provenance for FT5955.

No filesystem writes; no USB, fprintd, biometrics, Git fetch or credentials.
Does not print Git remotes' URLs, commit author/committer metadata, or diffs.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys

BASE = "c8e01dc26cedb2d97779a314a7260f1c33e02bfa"
CRITICAL = ("libfprint/meson.build", "libfprint/drivers/focaltech_5955.c")


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(root), *args],
        text=True, stderr=subprocess.PIPE, timeout=12
    ).strip()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--libfprint", default="~/Projects/libfprint-ft5955",
                        help="Existing experimental libfprint Git checkout (READ ONLY)")
    opts = parser.parse_args()
    root = Path(opts.libfprint).expanduser().resolve()
    if not root.is_dir() or git(root, "rev-parse", "--show-toplevel") != str(root):
        raise ValueError("Expected exact root of the existing local libfprint Git checkout")

    if git(root, "cat-file", "-t", BASE) != "commit":
        raise ValueError("Pinned libfprint object missing or not a commit")
    line = git(root, "rev-list", "--parents", "-n", "1", BASE).split()
    if not line or line[0] != BASE:
        raise ValueError("Could not inspect pinned commit ancestry")
    parents = line[1:]
    print("PINNED_LIBFPRINT_COMMIT:", BASE)
    print("PARENT_COUNT:", len(parents))
    for i, parent in enumerate(parents, start=1):
        print(f"PARENT_{i}:", parent)

    for rel in CRITICAL:
        names = git(root, "ls-tree", "-r", "--name-only", BASE, "--", rel).splitlines()
        print("BASE_CONTAINS_" + rel.replace("/", "_").replace(".", "_").upper() + ":",
              "YES" if names == [rel] else "NO")

    # Only reference *counts*: avoid exposing remote URLs, user/branch names,
    # Git author email or detailed source content.
    for refkind, refpath in [
        ("LOCAL_BRANCHES", "refs/heads"),
        ("REMOTE_TRACKING_REFS", "refs/remotes"),
        ("TAGS", "refs/tags"),
    ]:
        names = git(root, "for-each-ref", f"--contains={BASE}",
                    "--format=%(refname)", refpath)
        count = len(names.splitlines()) if names else 0
        print(f"{refkind}_CONTAINING_BASE:", count)
        if refkind == "REMOTE_TRACKING_REFS" and count == 0:
            print("CAUTION: no *locally fetched* remote-tracking ref contains the base.")
    remotes = git(root, "remote")
    print("CONFIGURED_REMOTE_COUNT:", len(remotes.splitlines()) if remotes else 0)

    if parents:
        try:
            changed = git(root, "diff-tree", "--no-commit-id", "--name-only",
                          "-r", BASE, "--", *CRITICAL)
        except subprocess.CalledProcessError:
            changed = ""
        print("BASE_COMMIT_CHANGED_DRIVER_SCAFFOLD:",
              "YES" if changed else "NO")
    print("PASS: audit read Git metadata only; no changes or sensor operations.")
    print("NOTE: local remote-tracking refs do not prove a commit is still "
          "fetchable from an actual remote; a clean-clone test is needed.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, subprocess.CalledProcessError,
            subprocess.TimeoutExpired) as exc:
        sys.exit(f"BASE AUDIT STOPPED: {exc}")
