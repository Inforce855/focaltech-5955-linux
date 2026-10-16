#!/usr/bin/env python3
"""Offline reconstruction check for the 16-Oct-2026 FT5955 driver snapshot.

Default = read-only preflight. --build extracts a pristine, pinned libfprint
commit to a disposable /tmp tree, layers the recorded patch and source, then
builds libfprint there. No enrollment, scanner access, sudo, install, or
changes to existing Git worktrees/system authentication.
"""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile

BASE = "c8e01dc26cedb2d97779a314a7260f1c33e02bfa"
SNAP = Path("driver/live-snapshot-2026-10-16")
DRIVERS = (
    "focaltech_5955.c", "ft5955_action_core.c", "ft5955_action_core.h",
    "ft5955_fpi_action_bridge.c", "ft5955_fpi_action_bridge.h",
    "ft5955_fpi_print_bridge.c", "ft5955_fpi_print_bridge.h",
    "ft5955_native_action.c", "ft5955_native_action.h",
    "ft5955_native_capture.c", "ft5955_native_capture.h",
    "ft5955_print_codec.c", "ft5955_print_codec.h",
)
ENGINE = ("engine_gateway.py", "template_runner.py", "template_session.c")
PATCH = "patches/local-libfprint-changes.patch"


def execute(args: list[str], *, cwd: Path | None = None,
            stream: bool = False) -> str:
    print("RUN:", " ".join(args), flush=True)
    if stream:
        subprocess.run(args, cwd=cwd, check=True)
        return ""
    return subprocess.check_output(args, cwd=cwd, text=True).strip()


def get_manifest(snapshot: Path) -> dict[str, str]:
    manifest = (snapshot / "README.md").read_text(encoding="utf-8")
    if f"Base libfprint Git commit: {BASE}" not in manifest:
        raise ValueError("Pinned libfprint commit does not match manifest")
    values: dict[str, str] = {}
    for line in manifest.splitlines():
        m = re.fullmatch(r"([a-zA-Z0-9_./-]+): ([0-9a-f]{64})", line)
        if m:
            values[m.group(1)] = m.group(2)
    required = {f"libfprint/drivers/{n}" for n in DRIVERS}
    required.update(f"engine/{n}" for n in ENGINE)
    required.add(PATCH)
    if set(values) != required:
        raise ValueError(f"Snapshot manifest mismatch; absent={sorted(required-set(values))}, extra={sorted(set(values)-required)}")
    for name, expected in sorted(values.items()):
        p = snapshot / name
        if p.is_symlink() or not p.is_file():
            raise ValueError(f"Missing or symlinked snapshot source: {p}")
        if hashlib.sha256(p.read_bytes()).hexdigest() != expected:
            raise ValueError(f"Snapshot SHA-256 mismatch: {p}")
    return values


def archive_pinned_source(libfprint: Path, stage: Path) -> None:
    cmd = ["git", "-C", str(libfprint), "archive", "--format=tar", BASE]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert proc.stdout is not None
    try:
        # Data extraction filter rejects escaping paths and unsafe links.
        with tarfile.open(fileobj=proc.stdout, mode="r|") as archive:
            for item in archive:
                archive.extract(item, stage, filter="data")
        proc.stdout.close()
        error = proc.stderr.read().decode(errors="replace") if proc.stderr else ""
        if proc.wait() != 0:
            raise ValueError(f"git archive failed: {error}")
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
        if proc.stderr:
            proc.stderr.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--libfprint", default="~/Projects/libfprint-ft5955",
                        help="Existing local Git checkout (READ ONLY)")
    parser.add_argument("--build", action="store_true",
                        help="Run isolated temporary-source Meson compile (NO install)")
    args = parser.parse_args()
    if os.geteuid() == 0:
        raise ValueError("Refusing root; run as normal user")
    repo = Path(__file__).resolve().parent.parent
    snapshot = repo / SNAP
    libfprint = Path(args.libfprint).expanduser().resolve()
    if libfprint == repo or libfprint.is_relative_to(repo) or repo.is_relative_to(libfprint):
        raise ValueError("The source-history repo and upstream libfprint checkout must be separate")
    if not libfprint.is_dir() or not snapshot.is_dir():
        raise ValueError("Missing existing libfprint checkout or GitHub snapshot directory")
    get_manifest(snapshot)
    root = subprocess.check_output(
        ["git", "-C", str(libfprint), "rev-parse", "--show-toplevel"], text=True).strip()
    if Path(root).resolve() != libfprint:
        raise ValueError("--libfprint must point to the Git working-tree root")
    kind = execute(["git", "-C", str(libfprint), "cat-file", "-t", BASE])
    if kind != "commit":
        raise ValueError("Base libfprint object is not a commit")
    print("PASS: 13 C/header driver files, 3 engine sources and Meson patch verified by SHA-256")
    print("PASS: base libfprint commit available locally; active checkout will remain untouched")
    if not args.build:
        print("PREFLIGHT ONLY — no files changed, no fingerprint operation. Use --build to compile.")
        return
    for exe in ("git", "meson", "ninja"):
        if not shutil.which(exe):
            raise ValueError(f"Build dependency missing: {exe}")
    with tempfile.TemporaryDirectory(prefix="ft5955-rebuild-") as td:
        work = Path(td)
        source = work / "libfprint-source"
        source.mkdir()
        print("Extracting pinned libfprint commit to disposable /tmp directory...")
        archive_pinned_source(libfprint, source)
        patch = snapshot / PATCH
        execute(["git", "apply", "--check", str(patch)], cwd=source)
        execute(["git", "apply", str(patch)], cwd=source)
        # The recorded patch must reproduce the exact live main driver;
        # this is stronger than just a successful fuzzy patch application.
        main_name = "libfprint/drivers/focaltech_5955.c"
        expected_main = snapshot / main_name
        if (source / main_name).read_bytes() != expected_main.read_bytes():
            raise ValueError("Patch-derived focaltech_5955.c differs from saved live source")
        for name in DRIVERS:
            rel = Path("libfprint/drivers") / name
            target = source / rel
            if name != "focaltech_5955.c" and (target.exists() or target.is_symlink()):
                raise ValueError(f"Refusing to overwrite an upstream file: {rel}")
            if name != "focaltech_5955.c":
                shutil.copyfile(snapshot / rel, target)
        print("PASS: exact main driver reproduced; 12 additional saved driver sources layered")
        build = work / "build"
        execute(["meson", "setup", str(build), str(source),
                 "-Ddrivers=focaltech_5955", "-Ddoc=false",
                 "-Dintrospection=false"], cwd=work, stream=True)
        execute(["meson", "compile", "-C", str(build)], cwd=work, stream=True)
        libs = list((build / "libfprint").glob("libfprint-2.so*"))
        if not libs:
            raise ValueError("Build finished but expected libfprint shared library is absent")
        print("PASS: isolated libfprint build completed using GitHub snapshot")
    print("PASS: temporary rebuild removed; live checkout, system auth and USB device untouched")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError,
            tarfile.TarError) as exc:
        sys.exit(f"REBUILD STOPPED: {exc}")
