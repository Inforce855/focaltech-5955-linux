# Rebuild the preserved FT5955 driver without enrolment

**State: PASS on Nobara, 16 October 2026.** The isolated GitHub-snapshot source build completed successfully; hardware operation with the newly built copy was **not** tested. This is a preparation and compile test, not a verified native matcher or system integration. The source is pinned to the real private driver snapshot [live-snapshot-2026-10-16](../driver/live-snapshot-2026-10-16/README.md), preserved in commit [77db7f5](https://github.com/Inforce855/focaltech-5955-linux/commit/77db7f5).

## Confirmed Nobara build result — 16 October 2026

The user executed `python3 "$HISTORY/tools/verify_ft5955_rebuild.py" --build` after updating the source-history worktree from GitHub. The final terminal output showed:

```text
Build targets in project: 27
libfprint 1.94.100
Drivers: focaltech_5955
doc: false
drivers: focaltech_5955
introspection: false
Found ninja-1.13.2 at /usr/bin/ninja
RUN: meson compile -C /tmp/ft5955-rebuild-jd8r121t/build
[109/109] Linking target tests/test-fpi-device
PASS: isolated libfprint build completed using GitHub snapshot
PASS: temporary rebuild removed; live checkout, system auth and USB device untouched
```

**PASS criteria met:** Manifest-verified preserved driver/header sources and Meson patch reproduced the then-live main source on the pinned historical libfprint base, Meson configured the FocalTech-only driver, and the disposable source tree compiled to completion. The script reported removing the disposable build tree. The result was obtained **without fingerprint contact, enrolment, a hardware test, installation or modifying the existing active libfprint checkout**.

**Boundaries:** This test used the user's locally available upstream libfprint Git object at pinned commit; it does not independently test network clean-clone checkout, build across arbitrary machines, MOH matching gateway runtime, nor the binary against USB hardware. It proves a successful **source rebuild**, not that 109 test cases executed; `109/109` is Ninja's compiled build step count. The separate private-`fprintd` hardware trials established actual enrol/verify and template reuse on the earlier live build.

**Next no-enrolment work:** Assess a controlled use of the newly reproduced library for **device discovery/Claim only** on the already-proven private D-Bus stack, without touching enrolled templates, enrolling a finger or altering system PAM/fprintd. Before attempting such a test, the temporary build-cleanup workflow needs an opt-in way to preserve a testable build outside the live checkout and a bounded, clean-stop private test harness. Do not run an enrolment mode under any proposed new test.

## Purpose

Prove that the **13 previously working driver/header files**, plus the exact libfprint Meson changes, can recreate an isolated libfprint build independently of uncommitted working-copy modifications.

The tool [`tools/verify_ft5955_rebuild.py`](../tools/verify_ft5955_rebuild.py):

1. Verifies SHA-256 of all 13 driver/header sources, 3 experimental MOH gateway sources, and the tracked libfprint patch against the captured README manifest.
2. Checks the previously established base libfprint Git commit `c8e01dc26cedb2d97779a314a7260f1c33e02bfa` exists in the existing `~/Projects/libfprint-ft5955` Git object store.
3. With `--build`, extracts **that pinned historical commit** to a unique temporary directory under `/tmp`, using Git's archive interface. It **does not use** the current dirty working files and does **not** create a new persistent project directory or Git worktree.
4. Checks and applies the preserved `local-libfprint-changes.patch` to the temporary source; confirms that the resulting `focaltech_5955.c` is byte-for-byte identical to the captured live driver; layers the other 12 preserved source/header files.
5. Runs `meson setup` with `-Ddrivers=focaltech_5955 -Ddoc=false -Dintrospection=false` and then `meson compile` **only against the disposable source/build directories**, checks for a generated libfprint shared library, and deletes the temporary directory on exit.

The **engine gateway is checked for snapshot integrity but not launched or compiled** by this task; the proprietary MOH matcher is never required. **No biometric samples/templates, USB transfers, enrolment, fprintd, PolicyKit, sudo, installs, PAM, KDE, or system daemon changes.** The existing live private libfprint checkout is read-only throughout. On failure, the script reports the error and cleans up.

## On the user's Nobara computer

Existing source-history worktree was created previously at `~/Projects/ft5955-source-history`. Safely update it **without changing the current private libfprint checkout**:

```bash
HISTORY="$HOME/Projects/ft5955-source-history"
git -C "$HISTORY" status --short
git -C "$HISTORY" pull --ff-only
```

If the worktree has unrelated uncommitted edits or `pull --ff-only` fails, **stop rather than overwriting anything**.

Read-only check first:

```bash
python3 "$HISTORY/tools/verify_ft5955_rebuild.py"
```

Then isolated compile:

```bash
python3 "$HISTORY/tools/verify_ft5955_rebuild.py" --build
```

The latter is a **source rebuild only**, not a device test. It requires Python 3.12+, Git, Meson, Ninja and normal libfprint/OpenSSL C build dependencies on Nobara. It intentionally does not run `meson install`, `sudo`, `fprintd` or any program that scans fingerprints.

**Pass criteria (met on Nobara, 16 October 2026):** all recorded source SHA-256 values match; exact original libfprint commit is present; patch applies cleanly and reproduces the captured main driver; Meson configures and compiles a libfprint shared library in the temporary directory. The live driver remains unchanged.

**If it fails:** paste only the command output and compiler errors, not any fingerprint recordings, templates, /dev/shm files, or vendor binaries. A compile failure is a useful reproducibility finding, not proof that the previously tested live driver was broken.

## Not included yet

- A clean-clone build independent of the local upstream Git object store.
- A fully reproducible build environment with pinned OS/compiler/dependencies.
- Building/installing or enabling the separate MOH gateway or a new `fprintd`.
- System authentication / fingerprint login, persistent secret storage, or additional biometric enrolment.

After successful isolated compilation, document the exact result and choose the next **no-enrolment** integration check. Existing private-fprintd roundtrip and control results are recorded on [`feature/ft5955-private-fprintd-v096`](https://github.com/Inforce855/focaltech-5955-linux/blob/feature/ft5955-private-fprintd-v096/docs/status-2026-10-16.md).
