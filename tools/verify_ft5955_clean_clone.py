#!/usr/bin/env python3
"""Isolated FT5955 rebuild from publicly cloned libfprint v1.94.100.

Uses three source patches preserved and SHA-256 verified in this GitHub repo:
initial scanner scaffold, USB-descriptor validation, active driver/Meson patch.
Default without flags validates local sources only. --build fetches the exact
upstream tag into /tmp and compiles without installation, USB or enrolment.
--claim-only additionally runs the existing private no-enrolment Claim test.
Optional --poll-100ms builds an isolated, opt-in timing experiment ONLY;
the source snapshot, 500ms default build and system service stay unchanged.
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
CAPTURE_SOURCE = "libfprint/drivers/ft5955_native_capture.c"
VERIFY_SOURCE = "libfprint/drivers/ft5955_native_action.c"


def apply_poll100_variant(source: Path) -> None:
    """Patch ONLY the reconstructed disposable source, after manifest validation.

    100 ms x 1,200 polls = same approximate 120 second capture wait.
    Finger-edge logic, 10 ms settle time, USB commands and MOH engine unchanged.
    Refuse changed sources/ambiguous replacement rather than modifying more code.
    """
    target = source / CAPTURE_SOURCE
    if target.is_symlink() or not target.is_file():
        raise ValueError("Missing regular FT5955 capture source in disposable tree")
    data = target.read_text(encoding="utf-8")
    replacements = (
        (" * 240 polls (two minutes)", " * 1200 polls (two minutes)"),
        ("for(unsigned poll=0;poll<240;poll++) {",
         "for(unsigned poll=0;poll<1200;poll++) {"),
        ("gint64 pause=500000-(g_get_monotonic_time()-started);",
         "gint64 pause=100000-(g_get_monotonic_time()-started);"),
        ("No fresh FT5955 touch within 240 status checks",
         "No fresh FT5955 touch within 1200 status checks"),
    )
    for old, new in replacements:
        if data.count(old) != 1:
            raise ValueError(f"Capture timing source changed: expected one {old!r}")
        data = data.replace(old, new, 1)
    if data.count("g_usleep(10000);") != 1:
        raise ValueError("The original 10ms post-contact delay changed unexpectedly")
    target.write_text(data, encoding="utf-8")




def apply_bounded_verify(source: Path) -> None:
    """Implement four fresh NO_MATCH touches per ONE fprintd verify operation.

    The immutable, hash-pinned driver snapshot is reconstructed first. Only its
    disposable build copy changes. Quality retries continue independently;
    at most 16 total captures and 4 actual NO_MATCH replies are permitted.
    The MOH service stays in the same imported-template verification session.
    No partial NO_MATCH is reported to KDE; only a terminal match/failure.
    """
    target = source / VERIFY_SOURCE
    if target.is_symlink() or not target.is_file():
        raise ValueError("Missing regular FT5955 action source in disposable tree")
    data = target.read_text(encoding="utf-8")
    changes = (
        ("#define MAX_CAPTURES_VERIFY 16\n",
         "#define MAX_CAPTURES_VERIFY 16\n"
         "#define MAX_NO_MATCH_VERIFY 4 /* separate fresh finger contacts */\n"),
        ("  gboolean done=FALSE;\n  Ft5955Action guard;\n",
         "  gboolean done=FALSE;\n  unsigned no_match_attempts=0;\n  Ft5955Action guard;\n"),
        (
            "    if(!job->enrolling && (event==FT5955_DRIVER_MATCHED ||\n"
            "                            event==FT5955_DRIVER_NOT_MATCHED)) {\n"
            "      job->pending=event==FT5955_DRIVER_MATCHED;\n"
            "      done=TRUE;break;\n"
            "    }\n",
            "    if(!job->enrolling && event==FT5955_DRIVER_NOT_MATCHED) {\n"
            "      /* A mismatch is an ordinary imperfect touch, not an entire\n"
            "       * failed KDE unlock. The USB scanner requires a NEW OFF->ON\n"
            "       * transition for the next frame. Never reuse a held image.\n"
            "       * Preserve the global 16-frame bound and emit just one final\n"
            "       * libfprint verify report after success or four mismatches. */\n"
            "      if(++no_match_attempts<MAX_NO_MATCH_VERIFY && i+1<max) {\n"
            "        g_message(\"FT5955 no match; lift and press again (%u/%u)\",\n"
            "                  no_match_attempts,MAX_NO_MATCH_VERIFY);\n"
            "        ft5955_action_begin(&guard,FT5955_ACTION_VERIFY);\n"
            "        continue;\n"
            "      }\n"
            "      job->pending=FALSE;\n"
            "      done=TRUE;break;\n"
            "    }\n"
            "    if(!job->enrolling && event==FT5955_DRIVER_MATCHED) {\n"
            "      job->pending=TRUE;\n"
            "      done=TRUE;break;\n"
            "    }\n"
        ),
    )
    for old, new in changes:
        if data.count(old) != 1:
            raise ValueError("FT5955 verify source changed; refusing unsafe retry patch")
        data = data.replace(old, new, 1)
    target.write_text(data, encoding="utf-8")


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
    mode.add_argument("--stage", action="store_true",
                      help="Rebuild and stage verified .so in PRIVATE user state; NO install/USB")
    ap.add_argument("--poll-100ms", action="store_true",
                    help="Opt-in build with 100ms (not 500ms) contact polling; NO system/USB changes")
    args = ap.parse_args()
    if args.poll_100ms and args.claim_only:
        ap.error("--poll-100ms is not available for hardware Claim-only tests")
    if args.poll_100ms and not (args.build or args.stage):
        ap.error("--poll-100ms requires --build or --stage")
    if os.geteuid() == 0:
        raise ValueError("Run as a normal user; never root")
    repo = Path(__file__).resolve().parent.parent
    snapshot = repo / existing.SNAP
    existing.get_manifest(snapshot)
    patches = [source_patch_path(snapshot, p, digest) for p, digest in UPSTREAM_PATCHES]
    active_patch = snapshot / existing.PATCH
    print("PASS: saved working-driver source manifest and BOTH historical patch hashes verified")
    print("PASS: pinned upstream libfprint release tag =", UPSTREAM_TAG)
    if not (args.build or args.claim_only or args.stage):
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
        apply_bounded_verify(source)
        print("VERIFY IMPLEMENTED: up to 4 fresh touches in one fprintd/KDE request;")
        print("one final result, max 16 captures, cancellation preserved.")
        if args.poll_100ms:
            apply_poll100_variant(source)
            print("TIMING VARIANT ONLY: 100ms contact polls, 1200 checks (~2 min).")
            print("Unchanged: release-then-press gate, 10ms delay, USB protocol, matcher.")
            print("Source snapshot, installed system and normal 500ms build are untouched.")
        build = work / "build"
        existing.execute([
            "meson", "setup", str(build), str(source),
            "-Ddrivers=focaltech_5955", "-Ddoc=false", "-Dintrospection=false",
        ], cwd=work, stream=True)
        existing.execute(["meson", "compile", "-C", str(build)], cwd=work,
                         stream=True)
        if not list((build / "libfprint").glob("libfprint-2.so*")):
            raise ValueError("Build finished without a libfprint shared library")
        print("PASS: CLEAN upstream clone + 3 GitHub patches and bounded verification built")
        if args.stage:
            # User-owned staging only. Do not put the shared library where a
            # protected system fprintd service would load it. A separate
            # privileged trial tool will copy it into root-owned /opt later.
            stage_name = "stage-poll100" if args.poll_100ms else "stage"
            stage = Path.home() / ".local" / "state" / "ft5955-system-trial" / stage_name
            if stage.exists() or stage.is_symlink():
                raise ValueError(f"Stage already exists: {stage}; refusing overwrite")
            library = build / "libfprint" / "libfprint-2.so.2.0.0"
            if library.is_symlink() or not library.is_file():
                raise ValueError(f"Exact built libfprint SONAME target missing: {library}")
            # Ensure source executable remains ordinary ELF and was compiled
            # for the same runtime ABI; no hardware or system service involved.
            if library.open("rb").read(4) != b"\x7fELF":
                raise ValueError("Built library is not an ELF file")
            stage.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            stage.mkdir(mode=0o700)
            lib_stage = stage / "lib"
            lib_stage.mkdir(mode=0o700)
            staged = lib_stage / library.name
            shutil.copyfile(library, staged)
            os.chmod(staged, 0o600)
            digest = hashlib.sha256(staged.read_bytes()).hexdigest()
            manifest = stage / "SHA256"
            manifest.write_text(f"{digest}  lib/{library.name}\n", encoding="ascii")
            os.chmod(manifest, 0o600)
            print("PASS: verified clean build STAGED to user-only location:", stage)
            print("STAGED_LIB_SHA256:", digest)
            if args.poll_100ms:
                print("TIMING VARIANT STAGED SEPARATELY: ordinary system trial installers")
                print("do NOT load stage-poll100; never replace baseline stage by hand.")
            print("No files in /opt, /etc, /usr, no service/PAM edits and no USB operations.")
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
