# Next-session handoff — FT5955 on Nobara

**Current checkpoint: 17 October 2026.** The real standard Linux/KDE enrol → verify → rollback experiment was **successful**. The experimental system installation is **not active** after the user-confirmed rollback. Treat this note as the starting point for the next development session, not as instructions to redo the completed tests.

## What has been demonstrated

- FocalTech USB **`2808:5955`**, built into the machine's power button; it **cannot be physically unplugged** as a convenient test.
- Private `fprintd` enrol/retry/reopen/cancellation, two negative-finger checks, stored-template restart roundtrip and direct USB capture have already been exercised. **Do not restart from those tests.**
- Reproducible upstream `libfprint v1.94.100` source reconstruction (pinned `80a4b5ec612892c5c056c48dddaa561452cf37ec`), three verified patches, Ninja **109/109** build steps. Compiled library staged under `~/.local/state/ft5955-system-trial/stage/` (it may remain) with SHA-256 **`003ed7e6d53109ad355b653f3b5a9a6cfb33c99e150ae5e58ed7f6ff41fd7d4e`**. A successful compile is *not* a full upstream test-suite PASS.
- **Normal** system `fprintd` loaded the experimental library and reported the device. The user started the short-lived user-session MOH/bwrap broker, and the actual KDE System Settings → Users interface displayed **Configure Fingerprint Authentication**.
- **Both left and right index fingers enrolled successfully in KDE.** Standard `fprintd-verify` subsequently produced real `verify-match` results. User estimates **about 85% match success after 3–4 separate taps** (not a first-press estimate). Earlier observations show that a true lift/re-press is needed to get a fresh sensor image.
- `bash tools/ft5955_kde_trial.sh --stop` **PASSED** in the user's terminal: disabled the experimental gateway, removed the relay, dropped the dedicated `/opt` shared library and service override, and restored packaged Nobara `libfprint`/`fprintd`. **No PAM, SDDM or password-login changes.** The next normal activation was not independently mapped back to the package library, but the tested script confirmed rollback. A Timeshift snapshot was created before the trial; no restore was needed.
- Normal `fprintd` storage **may retain the two experimental enrolled templates** after rollback. That is separate from the staged local library and separate from the old private RAM-only templates.

## Current implementation layout

- **Current repository baseline:** **`main`** now contains the tested consolidation after [merged PR #4](https://github.com/Inforce855/focaltech-5955-linux/pull/4). The existing user checkout `~/Projects/ft5955-independent-build-check` tracks `feature/ft5955-driver-consolidation-20261017` and was **not silently switched to `main`** by the GitHub merge. Both branch histories are preserved. Check the local branch before updating or editing it; do not delete or rewrite the separate MOH/libfprint research checkouts.
- **Driver source of record:** [`driver/live-snapshot-2026-10-16/`](../driver/live-snapshot-2026-10-16/README.md), intentionally immutable due to checksum/patch provenance.
- **Clean upstream build and optional stage:** [`tools/verify_ft5955_clean_clone.py`](../tools/verify_ft5955_clean_clone.py).
- **System discovery-only install/rollback:** [`tools/manage_ft5955_system_trial.sh`](../tools/manage_ft5955_system_trial.sh).
- **Successful lab KDE start/stop:** [`tools/ft5955_kde_trial.sh`](../tools/ft5955_kde_trial.sh) and [`tools/manage_ft5955_kde_trial.sh`](../tools/manage_ft5955_kde_trial.sh); **not** a permanent installation/login setup.
- **User-session broker:** [`tools/ft5955_engine_broker.py`](../tools/ft5955_engine_broker.py), connecting normal root `fprintd` over a private AF_UNIX socket to the existing non-root MOH/bwrap process.
- **Existing MOH private loader:** expected at `~/Projects/focaltech-5955-moh-test`, with pinned Windows DLL at `/usr/local/lib/focaltech-5955/ftWbioEngineAdapter.dll`. User's read-only audit confirmed the installed root-owned DLL matches its pinned SHA-256.
- **Exact experiment and rollback evidence:** [`kde-short-lived-trial-2026-10-17.md`](kde-short-lived-trial-2026-10-17.md).

## What to do next — ordered by value

1. **Investigate one-touch recognition first.** Inspect `ft5955_native_capture.c`, the existing finger-on/off rearm behavior, buffering and sample selection. Compare the intended press/release state machine against the previous user observation that lifting and reapplying a finger triggers a genuinely new frame. Prefer synthetic/offline tests or precise review, **not more 12-impression enrolment or exhausting physical testing**. Don't assume that 85% after multiple taps is single-press accuracy.
2. **Make authentication trustworthy before making it persistent.** The current MOH C compilation contains `FT5955_ALLOW_UNVERIFIED_ATTACH`; the backend is **owned by the login user** while normal `fprintd` runs as root, and the saved-template envelope uses unkeyed SHA-256 for corruption detection, **not authenticity**. These are actual architecture limitations for production login. Review secure matcher separation, origin/policy and storage, cancel/timeout, anti-spoof/false-accept measurement. **PAM still absent in tested environment** and must not be enabled merely because lab enrolment passed.
3. **Finish native matching** to remove the Windows MOH DLL dependency when validated, building on [`native/`](../native/README.md).
4. Prepare a maintained *reversible* package/installation path only after safety/reliability criteria. Preserve the known-good password login and original vendor libraries.

## Completed alternatives to avoid revisiting

- An extra hardened `ft5955-engine-smoke.service` with a fake engine **passed** non-root socket/UID tests, but **nested bubblewrap inside that service failed** (`ERROR BWRAP_NAMESPACE_UNAVAILABLE`). Temporary units, socket and service account were removed. The team deliberately **stopped pursuing double sandboxing** and succeeded with the existing user-session MOH/bwrap route instead.
- USB Claim permissions in the earlier private test required a temporary ACL on the identified device node. The standard system service already had USB access; no separate physical unplug test is necessary.
- **GitHub housekeeping, 17 October:** [consolidation PR #4](https://github.com/Inforce855/focaltech-5955-linux/pull/4) was **merged into `main`** with full history; the fully represented earlier private-[`fprintd` PR #2](https://github.com/Inforce855/focaltech-5955-linux/pull/2) was **closed as superseded without deleting its branch**. The older [MOH engine research PR #1](https://github.com/Inforce855/focaltech-5955-linux/pull/1) stays **open** because it contains substantial additional `engine/` code and tests not yet reviewed for merging to `main`. **Do not delete those branches, run `git clean` in live trees, or rewrite the pinned snapshot.**

## Safe operational note

The **lab trial was fully rolled back**; no additional commands are needed to keep the normal system in its existing state. If a future trial is deliberately authorised, consult the actual [documented setup and stop scripts](kde-short-lived-trial-2026-10-17.md), check OS versions and exact rollback rather than assuming the environment has not changed. Never commit actual fingerprint data, vendor DLLs or sensitive logs.
