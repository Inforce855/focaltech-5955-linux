# Rebuild the preserved FT5955 driver without enrolment

**State: tool committed on 16 October 2026; clean-source hardware-independent build not yet executed on Nobara.** This is a preparation and compile test, not a verified native matcher or system integration. The source is pinned to the real private driver snapshot [live-snapshot-2026-10-16](../driver/live-snapshot-2026-10-16/README.md), preserved in commit [77db7f5](https://github.com/Inforce855/focaltech-5955-linux/commit/77db7f5).

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

**Pass criteria:** all recorded source SHA-256 values match; exact original libfprint commit is present; patch applies cleanly and reproduces the captured main driver; Meson configures and compiles a libfprint shared library in the temporary directory. The live driver remains unchanged.

**If it fails:** paste only the command output and compiler errors, not any fingerprint recordings, templates, /dev/shm files, or vendor binaries. A compile failure is a useful reproducibility finding, not proof that the previously tested live driver was broken.

## Not included yet

- A clean-clone build independent of the local upstream Git object store.
- A fully reproducible build environment with pinned OS/compiler/dependencies.
- Building/installing or enabling the separate MOH gateway or a new `fprintd`.
- System authentication / fingerprint login, persistent secret storage, or additional biometric enrolment.

After successful isolated compilation, document the exact result and choose the next **no-enrolment** integration check. Existing private-fprintd roundtrip and control results are recorded on [`feature/ft5955-private-fprintd-v096`](https://github.com/Inforce855/focaltech-5955-linux/blob/feature/ft5955-private-fprintd-v096/docs/status-2026-10-16.md).
