#!/usr/bin/env python3
"""Preserve the live private FT5955 driver without modifying its source tree.

Dry-run by default. --publish copies just reviewed text sources, makes a
snapshot-only commit and pushes on feature/ft5955-source-history. Never
executes installers, changes fprintd/PAM or touches the active driver.
"""
from __future__ import annotations
import argparse
import hashlib
from pathlib import Path
import subprocess

BRANCH = "feature/ft5955-source-history"
DEST = Path("driver/live-snapshot-2026-10-16")
DRIVERS = (
    "focaltech_5955.c",
    "ft5955_action_core.c", "ft5955_action_core.h",
    "ft5955_fpi_action_bridge.c", "ft5955_fpi_action_bridge.h",
    "ft5955_fpi_print_bridge.c", "ft5955_fpi_print_bridge.h",
    "ft5955_native_action.c", "ft5955_native_action.h",
    "ft5955_native_capture.c", "ft5955_native_capture.h",
    "ft5955_print_codec.c", "ft5955_print_codec.h",
)
ENGINE = ("engine_gateway.py", "template_runner.py", "template_session.c")


def git(root, *args):
    return subprocess.check_output(
        ["git", "-C", str(root), *args], text=True).strip()


def read_source(root, relative):
    path = root / relative
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"Missing or nonregular source: {path}")
    if path.stat().st_size > 2_000_000:
        raise ValueError(f"Oversized source: {path}")
    data = path.read_bytes()
    decoded = data.decode("utf-8")
    if "\x00" in decoded or "-----BEGIN PRIVATE KEY-----" in decoded:
        raise ValueError(f"Unexpected contents: {path}")
    return data


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", default="~/Projects/libfprint-ft5955")
    p.add_argument("--engine",
                   default="~/Projects/ft5955-driver-integration-v0.8/engine")
    p.add_argument("--repo", default="~/Projects/ft5955-source-history")
    p.add_argument("--publish", action="store_true")
    a = p.parse_args()
    src = Path(a.source).expanduser().resolve()
    engine = Path(a.engine).expanduser().resolve()
    repo = Path(a.repo).expanduser().resolve()
    if src == repo or engine == repo or repo.is_relative_to(src):
        raise ValueError("Snapshot checkout must be separate from live source")
    if not (src / "libfprint/drivers").is_dir():
        raise ValueError(f"Not a private libfprint source tree: {src}")
    if git(src, "rev-parse", "--show-toplevel") != str(src):
        raise ValueError(f"Source Git root differs: {src}")

    planned = {}
    for name in DRIVERS:
        planned[DEST / "libfprint/drivers" / name] = read_source(
            src, f"libfprint/drivers/{name}")
    read_source(src, "libfprint/meson.build")

    diff = subprocess.run(
        ["git", "-C", str(src), "diff", "--binary", "--",
         "libfprint/meson.build", "libfprint/drivers/focaltech_5955.c",
         "meson.build"],
        check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout
    if not diff or b"libfprint/meson.build" not in diff:
        raise ValueError("Expected tracked Meson diff missing; inspect before export")
    planned[DEST / "patches/local-libfprint-changes.patch"] = diff

    included_engine = []
    if not (engine / "engine_gateway.py").is_file():
        raise ValueError(f"Missing current engine gateway: {engine}")
    for name in ENGINE:
        if (engine / name).is_file():
            planned[DEST / "engine" / name] = read_source(engine, name)
            included_engine.append(name)
        else:
            print(f"NOTE: optional engine companion missing: {name}")

    manifest = [
        "# FT5955 live driver source snapshot — 16 October 2026",
        "",
        "Captured from the experimental private checkout, not the old archive.",
        "Historical reference only until building/testing from this snapshot.",
        "",
        f"Base libfprint Git commit: {git(src, 'rev-parse', 'HEAD')}",
        "",
        "The patches directory preserves local changes to the tracked Meson",
        "and main driver source relative to the commit above. All 13 active",
        "driver/header source files are preserved in libfprint/drivers.",
        "Obsolete backup copies, biometric data and vendor binaries excluded.",
        "",
        "Gateway files: " + ", ".join(included_engine),
        "",
        "## SHA-256 file hashes",
        "",
    ]
    for dest, data in sorted(planned.items()):
        manifest.append(
            f"{dest.relative_to(DEST).as_posix()}: "
            f"{hashlib.sha256(data).hexdigest()}")
    planned[DEST / "README.md"] = ("\n".join(manifest) + "\n").encode()

    for rel, data in planned.items():
        target = repo / rel
        if any(repo.joinpath(*rel.parts[:i]).is_symlink()
               for i in range(1, len(rel.parts) + 1)):
            raise ValueError(f"Refusing symlink in output path: {target}")
        if target.exists() and target.read_bytes() != data:
            raise ValueError(f"Existing snapshot differs; refusing overwrite: {target}")

    print(f"Validated: {len(DRIVERS)} live driver source files, "
          f"{len(included_engine)} engine sources, 1 patch, 1 manifest.")
    if not a.publish:
        print("DRY RUN ONLY — nothing changed.")
        return

    if git(repo, "rev-parse", "--show-toplevel") != str(repo):
        raise ValueError(f"Not a Git worktree root: {repo}")
    if git(repo, "branch", "--show-current") != BRANCH:
        raise ValueError(f"Wrong worktree branch; expected {BRANCH}")
    if git(repo, "status", "--porcelain"):
        raise ValueError("History worktree is dirty; nothing changed")
    if git(repo, "rev-parse", "HEAD") != git(repo, "rev-parse", f"origin/{BRANCH}"):
        raise ValueError("History worktree and origin differ; nothing changed")

    for rel, data in planned.items():
        target = repo / rel
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
    git(repo, "add", "--", DEST.as_posix())
    names = git(repo, "diff", "--cached", "--name-only").splitlines()
    if not names:
        print("Snapshot already committed; nothing to push.")
        return
    if any(not x.startswith(DEST.as_posix() + "/") for x in names):
        raise ValueError("Unexpected staged path; refusing commit")
    print(f"Committing {len(names)} snapshot files")
    git(repo, "commit", "-m",
        "Preserve live FT5955 driver, Meson integration patch and MOH gateway")
    git(repo, "push", "origin", BRANCH)
    print("PUSHED:", git(repo, "rev-parse", "--short", "HEAD"))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError,
            UnicodeError) as exc:
        raise SystemExit(f"SNAPSHOT STOPPED: {exc}") from exc
