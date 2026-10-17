#!/usr/bin/env python3
"""Read-only ancestry and source-patch audit of initial FT5955 libfprint scaffold.

Uses existing local Git objects only. No worktree edits, Git fetch, root,
fingerprint scans/enrolment, system fprintd, templates, or build operations.
"""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import subprocess
import sys

INITIAL = "68696e04a88efbecd5dd79cebf05b8ef013c51d8"
UPSTREAM_PARENT = "80a4b5ec612892c5c056c48dddaa561452cf37ec"
TAG = "v1.94.100"
EXPECTED = {
    "meson.build": "M",
    "libfprint/meson.build": "M",
    "libfprint/drivers/focaltech_5955.c": "A",
}
MAX_PATCH = 40000


def git(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, check=check,
        timeout=20,
    )


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--libfprint", default="~/Projects/libfprint-ft5955",
                   help="Local libfprint checkout to inspect (never modified)")
    p.add_argument("--show-patch", action="store_true",
                   help="Print complete vetted source-only scaffold diff")
    opts = p.parse_args()
    if os.geteuid() == 0:
        raise ValueError("Never run as root")
    root = Path(opts.libfprint).expanduser().resolve()
    if not root.is_dir():
        raise ValueError("Missing original Git checkout")
    top = git(root, "rev-parse", "--show-toplevel").stdout.decode().strip()
    if Path(top).resolve() != root:
        raise ValueError("Expected exact libfprint Git working-tree root")
    for commit in (INITIAL, UPSTREAM_PARENT):
        if git(root, "cat-file", "-t", commit).stdout.strip() != b"commit":
            raise ValueError(f"Expected Git commit not present: {commit}")
    parents = git(root, "rev-list", "--parents", "-n", "1", INITIAL).stdout.decode().split()
    if parents != [INITIAL, UPSTREAM_PARENT]:
        raise ValueError("Scaffold commit ancestry does not match audited history")
    tagproc = git(root, "rev-parse", "--verify", "--quiet",
                  TAG + "^{commit}", check=False)
    if tagproc.returncode != 0:
        raise ValueError("Local v1.94.100 tag is absent or invalid")
    tag_sha = tagproc.stdout.decode().strip()
    print("RELEASE_TAG:", TAG)
    print("TAG_COMMIT:", tag_sha)
    print("SCAFFOLD_PARENT:", UPSTREAM_PARENT)
    print("SCAFFOLD_COMMIT:", INITIAL)
    print("TAG_EQUALS_PARENT:", "YES" if tag_sha == UPSTREAM_PARENT else "NO")
    reachable = git(root, "merge-base", "--is-ancestor", tag_sha, UPSTREAM_PARENT,
                    check=False)
    if reachable.returncode not in (0, 1):
        raise ValueError("Could not check tag ancestry")
    print("TAG_IS_ANCESTOR_OF_PARENT:",
          "YES" if reachable.returncode == 0 else "NO")
    if reachable.returncode == 0:
        count = git(root, "rev-list", "--count",
                    f"{tag_sha}..{UPSTREAM_PARENT}").stdout.decode().strip()
        print("COMMITS_AFTER_RELEASE_TAG_TO_PARENT:", count)
        if tag_sha != UPSTREAM_PARENT:
            other_changes = git(
                root, "diff", "--no-ext-diff", "--no-textconv", "--name-only",
                tag_sha, UPSTREAM_PARENT,
            ).stdout.decode("utf-8").splitlines()
            print("FILES_DIFFERING_TAG_TO_PARENT:", len(other_changes))
            for name in other_changes:
                print("  upstream-gap:", name)

    raw = git(root, "diff", "--no-ext-diff", "--no-textconv", "--no-renames",
              "--name-status", "-z", UPSTREAM_PARENT, INITIAL).stdout
    parts = raw.split(b"\x00")
    if not parts or parts.pop() != b"" or len(parts) % 2:
        raise ValueError("Unrecognised name-status diff")
    changes = {}
    for j in range(0, len(parts), 2):
        status, name = parts[j].decode("ascii"), parts[j+1].decode("utf-8")
        changes[name] = status
    print("SCAFFOLD_CHANGED_FILE_COUNT:", len(changes))
    for name, status in sorted(changes.items()):
        print(" ", status, name)
    if changes != EXPECTED:
        raise ValueError("Unexpected changed files or statuses: do not publish patch")

    for name in changes:
        result = git(root, "ls-tree", INITIAL, "--", name).stdout.decode().strip()
        if not result.startswith("100644 blob "):
            raise ValueError(f"Unexpected scaffold file mode: {name}")

    patch = git(root, "diff", "--no-ext-diff", "--no-textconv", "--no-renames",
                "--binary", UPSTREAM_PARENT, INITIAL,
                "--", *sorted(EXPECTED)).stdout
    if not patch.startswith(b"diff --git ") or len(patch) > MAX_PATCH:
        raise ValueError("Scaffold patch invalid or unexpectedly large")
    if b"\x00" in patch or b"GIT binary patch" in patch:
        raise ValueError("Binary patch refused")
    patch_text = patch.decode("utf-8")
    print("SCAFFOLD_PATCH_BYTES:", len(patch))
    print("SCAFFOLD_PATCH_SHA256:", hashlib.sha256(patch).hexdigest())
    print("PASS: tag relationship and initial scaffold patch inspected READ ONLY.")
    print("NOTE: local tag is NOT proof of a publicly fetchable upstream revision.")
    if opts.show_patch:
        print("=== BEGIN COMPLETE SCAFFOLD PATCH ===")
        print(patch_text, end="" if patch_text.endswith("\n") else "\n")
        print("=== END COMPLETE SCAFFOLD PATCH ===")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, UnicodeError, subprocess.CalledProcessError,
            subprocess.TimeoutExpired) as exc:
        sys.exit(f"SCAFFOLD ORIGIN AUDIT STOPPED: {exc}")
