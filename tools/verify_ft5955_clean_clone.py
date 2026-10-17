#!/usr/bin/env python3
"""Isolated FT5955 rebuild from publicly cloned libfprint v1.94.100.

Uses three source patches preserved and SHA-256 verified in this GitHub repo:
initial scanner scaffold, USB-descriptor validation, active driver/Meson patch.
Default without flags validates local sources only. --build fetches the exact
upstream tag into /tmp and compiles without installation, USB or enrolment.
--claim-only additionally runs the existing private no-enrolment Claim test.
Does not inspect or change ~/Projects/libfprint-ft5955 or system auth.
"""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import verify_ft5955_rebuild as existing

UPSTREAM_URL = "https://gitlab.freedesktop.org/libfprint/libfprint.git"
UPSTREAM_TAG = "v1.94.100"
UPSTREAM_COMMIT = "80a4b5ec612892c5c056c48dddaa561452cf37ec"
UPSTREAM_PATCHES = (
    ("patches/upstream-v1.94.100-to-initial-scaffold.patch",
     "5a4f80b925ad2640689f1748fb175ca0b01650ebb697da8d74743cf7080047cd"),
    ("patches/parent-to-base-usb-descriptor.patch",
     "df8af5a8ac10b716266bb8bdc1107a74c4714079e506a083b2579efa4c5d44f9"),
)
REQUIRED_SOURCE = "libfprint/drivers/focaltech_5955.c"


def source_patch_path(snapshot: Path, rel: str, expected_sha256: str) -> Path:
    path = snapshot / rel
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"Patch missing or a symlink: {rel}")
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != expected_sha256:
        raise ValueError(f"Verified patch SHA-256 differs from recorded value: {rel}")
    return path


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--build", action="store_true",
                      help="Fetch exact upstream release and compile in /tmp (NO USB)")
    mode.add_argument("--claim-only", action="store_true",
                      help="Rebuild then private Discover/Claim/Release (NO ENROL/VERIFY)")
    args = ap.parse_args()
    if os.geteuid() == 0:
        raise ValueError("Run as a normal user; never root")
    repo = Path(__file__).resolve().parent.parent
    snapshot = repo / existing.SNAP
    existing.get_manifest(snapshot)
    patches = [source_patch_path(snapshot, p, digest) for p, digest in UPSTREAM_PATCHES]
    active_patch = snapshot / existing.PATCH
    print("PASS: saved working-driver source manifest and BOTH historical patch hashes verified")
    print("PASS: pinned upstream libfprint release tag =", UPSTREAM_TAG)
    if not (args.build or args.claim_only):
        print("SOURCE PREFLIGHT ONLY: no network, USB, build or installation.")
        return
    for command in ("git", "meson", "ninja"):
        if not shutil.which(command):
            raise ValueError(f"Missing build command: {command}")
    claim_script = repo / "experiments/private-fprintd/ft5955_claim_only_v097.sh"
    if args.claim_only:
        if not claim_script.is_file():
            raise ValueError("Missing dedicated claim-only private bus launcher")
        existing.execute(["bash", str(claim_script), "--check"], cwd=repo, stream=True)
    with tempfile.TemporaryDirectory(prefix="ft5955-rebuild-", dir="/tmp") as td:
        work = Path(td)
        source = work / "libfprint-source"
        # Explicit upstream release source, not any object from the live/dirty checkout.
        print("Fetching upstream libfprint release to a disposable directory...", flush=True)
        subprocess.run([
            "git", "clone", "--quiet", "--depth", "1", "--single-branch",
            "--branch", UPSTREAM_TAG, UPSTREAM_URL, str(source),
        ], cwd=work, check=True, timeout=180)
        actual = subprocess.check_output(
            ["git", "-C", str(source), "rev-parse", "HEAD"], text=True,
        ).strip()
        if actual != UPSTREAM_COMMIT:
            raise ValueError("Upstream tag HEAD mismatch; refusing to apply patches")
        print("PASS: fresh upstream clone at exact released commit", actual)
        if (source / REQUIRED_SOURCE).exists():
            raise ValueError("Unexpected FocalTech 5955 driver already present upstream")
        for patch in (*patches, active_patch):
            existing.execute(["git", "apply", "--check", str(patch)], cwd=source)
            existing.execute(["git", "apply", str(patch)], cwd=source)
            print("PASS: applied reviewed source patch:", patch.name)
        expected_main = snapshot / REQUIRED_SOURCE
        if (source / REQUIRED_SOURCE).read_bytes() != expected_main.read_bytes():
            raise ValueError("Reconstructed C driver differs from SHA-verified working snapshot")
        for name in existing.DRIVERS:
            if name == "focaltech_5955.c":
                continue
            rel = Path("libfprint/drivers") / name
            dest = source / rel
            if dest.exists() or dest.is_symlink():
                raise ValueError(f"Refusing overwrite: {rel}")
            shutil.copyfile(snapshot / rel, dest)
        print("PASS: exact active driver and all additional sources reconstructed")
        build = work / "build"
        existing.execute([
            "meson", "setup", str(build), str(source),
            "-Ddrivers=focaltech_5955", "-Ddoc=false", "-Dintrospection=false",
        ], cwd=work, stream=True)
        existing.execute(["meson", "compile", "-C", str(build)], cwd=work,
                         stream=True)
        if not list((build / "libfprint").glob("libfprint-2.so*")):
            raise ValueError("Build finished without a libfprint shared library")
        print("PASS: CLEAN upstream clone + 3 GitHub patches built independently")
        if args.claim_only:
            env = os.environ.copy()
            env["FT5955_REBUILD_CLAIM_TEST"] = "1"
            env["FT5955_PRIVATE_LIB_DIR"] = str(build / "libfprint")
            print("=== PRIVATE NO-ENROLMENT HARDWARE CHECK ===", flush=True)
            subprocess.run(["bash", str(claim_script), "--claim-only"],
                           cwd=repo, env=env, check=True, timeout=100)
            print("PASS: fresh-clone driver Discover/Claim/Release verified")
    print("PASS: disposable source and build removed; live driver, system fprintd, PAM unchanged.")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError,
            subprocess.TimeoutExpired, FileNotFoundError) as exc:
        sys.exit(f"CLEAN CLONE BUILD STOPPED: {exc}")
