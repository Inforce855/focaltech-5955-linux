#!/usr/bin/env python3
"""Isolated FT5955 rebuild from publicly cloned libfprint v1.94.100.

Uses three source patches preserved and SHA-256 verified in this GitHub repo:
initial scanner scaffold, USB-descriptor validation, active driver/Meson patch.
Default without flags validates local sources only. --build fetches the exact
upstream tag into /tmp and compiles without installation, USB or enrolment.
--claim-only additionally runs the existing private no-enrolment Claim test.
Optional --poll-100ms builds a 100ms poll-only variant.
Optional --early-capture builds a SECOND isolated variant (100ms polling plus
parallel MOH startup and immediate finger monitoring on VERIFY only).
The source snapshot, earlier stages and system service stay unchanged.
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
ACTION_SOURCE = "libfprint/drivers/ft5955_native_action.c"


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



def source_patch_path(snapshot: Path, rel: str, expected_sha256: str) -> Path:
    path = snapshot / rel
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"Patch missing or a symlink: {rel}")
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != expected_sha256:
        raise ValueError(f"Verified patch SHA-256 differs from recorded value: {rel}")
    return path


def apply_earlycapture_variant(source: Path) -> None:
    """Only edit disposable native action; verify captures while matcher starts.

    Enrol remains completely unchanged. The image is consumed by MOH only
    after READY; the operation cancellable reaches both USB and MOH I/O.
    A cancelled or failed scan cancels/joins startup and cleans up.
    No new hardware opcodes, template storage, PAM or alternate matching engine.
    """
    target = source / ACTION_SOURCE
    if target.is_symlink() or not target.is_file():
        raise ValueError("Missing regular FT5955 action source in disposable tree")
    original = target.read_text(encoding="utf-8")

    init_anchor = "static gboolean parse_template (FtJob *job,GInputStream *in,GCancellable *c,GError **err) {"
    parallel_init = """/* Independent from the USB worker: MOH cannot delay contact observation.
 * Owned by the worker, which always joins this thread before returning.
 * Only the verify path uses this; enrolling stays on the established path. */
typedef struct {
  FtJob *job;
  GCancellable *cancel;
  GSubprocess *child;
  GInputStream *in;
  GOutputStream *out;
  GError *error;
  gboolean ready;
} FtGatewayStartup;

static gpointer gateway_start_parallel (gpointer arg) {
  FtGatewayStartup *s=arg;
  s->ready=start_gateway(s->job,&s->child,&s->in,&s->out,s->cancel,&s->error) &&
           startup(s->job,s->in,s->out,s->cancel,&s->error);
  return NULL;
}

"""
    old_launch = "  if(!start_gateway(job,&child,&in,&out,c,&err) || !startup(job,in,out,c,&err))goto end;"
    new_launch = """  /* Enrol keeps the known-good serial startup. Verify starts USB scanning
   * immediately while MOH initialises on an independent helper thread. */
  if(job->enrolling) {
    if(!start_gateway(job,&child,&in,&out,c,&err) || !startup(job,in,out,c,&err))goto end;
  } else {
    init.cancel=c; /* shared cancellable also stops gateway on fprintd cancel */
    init_thread=g_thread_new("ft5955-gateway-start",gateway_start_parallel,&init);
  }"""
    old_scan = "    if(!ft5955_native_scan(job->usb,c,frame,&err))goto end;"
    new_scan = """    if(!ft5955_native_scan(job->usb,c,frame,&err))goto end;
    if(init_thread) {
      /* A single captured image stays in worker RAM until the matcher
       * finishes startup. No other thread touches the USB device. */
      g_thread_join(init_thread);
      init_thread=NULL;
      child=init.child; in=init.in; out=init.out;
      if(!init.ready) {
        err=g_steal_pointer(&init.error);
        if(!err)
          g_set_error_literal(&err,G_IO_ERROR,G_IO_ERROR_FAILED,
                              "FT5955 matcher startup failed");
        goto end;
      }
    }"""
    old_end = "end:\n  sensitive_clear(frame,sizeof frame);"
    new_end = """end:
  /* If a capture fails or is cancelled during startup, cancel the MOH
   * handshake then join it BEFORE freeing the job or closing the process. */
  if(init_thread) {
    if(c)g_cancellable_cancel(c);
    g_thread_join(init_thread);
    init_thread=NULL;
    child=init.child; in=init.in; out=init.out;
  }
  g_clear_error(&init.error);
  sensitive_clear(frame,sizeof frame);"""
    old_vars = "  Ft5955Action guard;\n  ft5955_action_begin"
    new_vars = "  FtGatewayStartup init={.job=job};\n  GThread *init_thread=NULL;\n  Ft5955Action guard;\n  ft5955_action_begin"
    patches = ((init_anchor, parallel_init + init_anchor),
               (old_vars,new_vars),
               (old_launch,new_launch),
               (old_scan,new_scan),
               (old_end,new_end))
    data=original
    for old,new in patches:
        if data.count(old) != 1:
            raise ValueError(f"Unexpected native action anchor: {old[:75]!r}")
        data=data.replace(old,new,1)
    if data.count("if(job->enrolling)") < 2:
        raise ValueError("Unexpected enrol/verify split")
    target.write_text(data,encoding="utf-8")


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
    ap.add_argument("--early-capture", action="store_true",
                    help="100ms status polling + parallel verify matcher startup/early USB capture (experimental)")
    args = ap.parse_args()
    if args.poll_100ms and args.early_capture:
        ap.error("Select only one of --poll-100ms and --early-capture")

    if (args.poll_100ms or args.early_capture) and args.claim_only:
        ap.error("timing experiments are not available for hardware Claim-only tests")
    if (args.poll_100ms or args.early_capture) and not (args.build or args.stage):
        ap.error("timing experiment requires --build or --stage")
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
        if args.poll_100ms or args.early_capture:
            apply_poll100_variant(source)
            print("TIMING VARIANT: 100ms contact polls, 1200 checks (~2 min).")
            print("Unchanged: release-then-press gate, 10ms delay, USB commands, matcher.")
        if args.early_capture:
            apply_earlycapture_variant(source)
            print("EARLY CAPTURE (verify only): start matcher init on separate thread;")
            print("poll/capture USB immediately, then await matcher READY before FRAME.")
            print("ENROLL path unchanged. All images kept in worker memory.")
        if args.poll_100ms or args.early_capture:
            print("Source snapshot, installed system and baseline stages are untouched.")
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
        if args.stage:
            # User-owned staging only. Do not put the shared library where a
            # protected system fprintd service would load it. A separate
            # privileged trial tool will copy it into root-owned /opt later.
            stage_name = ("stage-earlycapture" if args.early_capture else
                          "stage-poll100" if args.poll_100ms else "stage")
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
            if args.poll_100ms or args.early_capture:
                print("TIMING VARIANT STAGED SEPARATELY: never replace earlier stages by hand.")
                print("Installer loads the new stage ONLY via explicit --start-earlycapture.")
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
