# Next-session handoff — FT5955 on Nobara

**Current checkpoint: 17 October 2026.** The real standard Linux/KDE enrol → verify → rollback experiment was **successful**. The experimental system installation is **not active** after the user-confirmed rollback. Treat this note as the starting point for the next development session, not as instructions to redo the completed tests.

## What has been demonstrated

- FocalTech USB **`2808:5955`**, built into the machine's power button; it **cannot be physically unplugged** as a convenient test.
- Private `fprintd` enrol/retry/reopen/cancellation, two negative-finger checks, stored-template restart roundtrip and direct USB capture have already been exercised. **Do not restart from those tests.**
- Reproducible upstream `libfprint v1.94.100` source reconstruction (pinned `80a4b5ec612892c5c056c48dddaa561452cf37ec`), three verified patches, Ninja **109/109** build steps. Compiled library staged under `~/.local/state/ft5955-system-trial/stage/` (it may remain) with SHA-256 **`003ed7e6d53109ad355b653f3b5a9a6cfb33c99e150ae5e58ed7f6ff41fd7d4e`**. A successful compile is *not* a full upstream test-suite PASS.
- **Normal** system `fprintd` loaded the experimental library and reported the device. The user started the short-lived user-session MOH/bwrap broker, and the actual KDE System Settings → Users interface displayed **Configure Fingerprint Authentication**.
- **Both left and right index fingers enrolled successfully in KDE.** Standard `fprintd-verify` subsequently produced real `verify-match` results. User estimates **about 85% match success after 3–4 rapid taps** (not a first-press estimate). **18 October clarification:** rapid tapping worked better than a single deliberate lift-and-press/hold; do not rephrase this as 'slow lift and press gives the best outcome'. Tapping does involve momentary separation but its short, repeated contacts may interact with the current polling/capture timing.
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

1. **Investigate one-touch recognition first (source-reviewed 18 October):** [native capture code](../driver/live-snapshot-2026-10-16/libfprint/drivers/ft5955_native_capture.c) polls `0x82` status every **500 ms**, starts `armed=FALSE` and **requires an observed `0x06` (off)** before accepting `0x05` (on); it then waits only **10 ms** before a single `0x80` readiness query and the `0x81` image read. Brief taps/releases may be missed between half-second polls, and the 10-ms image timing may be too early for full contact. The readiness marker `0x5AA5` was previously observed even at idle; **it is not independently proven to mean a fresh stable image**. The `500 ms` value was inherited from the conservative **early** [automatic contact viewer](../tools/auto_contact_capture.py), not benchmarked for reliable KDE verification. **Test one change at a time:** a separate opt-in timing-only variant with ~100-ms status polling and the **same 120-second overall bound**, keeping all USB commands and the 10-ms post-detect delay otherwise unchanged initially. Investigate post-press settling *only if* contact-edge improvement is insufficient. Preserve the hash-pinned snapshot/patch-chain, use offline synthetic trace tests, and do not re-enrol merely to test timing. No hardware timing variant built/tested as of this note.
2. **Make authentication trustworthy before making it persistent.** The current MOH C compilation contains `FT5955_ALLOW_UNVERIFIED_ATTACH`; the backend is **owned by the login user** while normal `fprintd` runs as root, and the saved-template envelope uses unkeyed SHA-256 for corruption detection, **not authenticity**. These are actual architecture limitations for production login. Review secure matcher separation, origin/policy and storage, cancel/timeout, anti-spoof/false-accept measurement. **PAM still absent in tested environment** and must not be enabled merely because lab enrolment passed.
3. **Finish native matching** to remove the Windows MOH DLL dependency when validated, building on [`native/`](../native/README.md).
4. Prepare a maintained *reversible* package/installation path only after safety/reliability criteria. Preserve the known-good password login and original vendor libraries.

## 18 October — timing experiment prepared, not yet tested on sensor

The user clarified that **holding a finger continuously produced no apparent read**, and that **a deliberate lift, wait and press also tended to fail**, while **3–4 rapid taps** led to substantially more `verify-match` outcomes. This suggests a contact/rearm/capture timing problem, but terminal `verify-no-match` versus absence of any capture should be distinguished; the original user report does not prove the image was never acquired.

The **existing, immutable** `ft5955_native_capture.c` requires an observed OFF (0x06) → ON (0x05) edge, polls at **500 ms**, then sleeps **10 ms** before a single readiness check and image request. Holding the finger at verify start, without any observed OFF, will not trigger this code. The previously observed readiness value 0x5AA5 does **not** prove a fresh stable image.

A **separate opt-in 100-ms polling variant** is now supported by [`verify_ft5955_clean_clone.py`](../tools/verify_ft5955_clean_clone.py) using `--poll-100ms` alongside `--build` or `--stage`. It edits **only the disposable rebuilt source**, after verifying the original snapshot hashes. The polling cap changes from 240 to 1,200 (preserving the roughly two-minute wait), while USB command bytes, OFF→ON gate, 10-ms delay, image conversion and matcher remain exactly the same. An offline [source-transformation test](../tests/test_ft5955_poll_timing.py) passed in GitHub Actions. `--stage --poll-100ms` writes to **`~/.local/state/ft5955-system-trial/stage-poll100`** instead of overwriting the known-good `stage`.

The existing lab KDE wrapper accepts opt-in `--start-poll100`, which passes only the specifically permitted variant stage name through both reversible activation scripts. **`--stop` remains the same as the user-tested rollback.** This is a new path that has passed offline syntax and source checks but **has not been compiled on Nobara or tested with live fprintd/USB**. Do not enable PAM or automatically enrol more fingers. If the two KDE enrolments still exist after rollback, compare one or two normal `fprintd-verify` results, especially whether it says `verify-no-match` or waits indefinitely. Only consider changing the 10-ms post-contact delay **later**, if 100-ms contact polling is insufficient. Do not claim improved recognition without the user's real test.

**Build/stage preparation (normal user, offline except upstream source fetch):**

```bash
REPO="$HOME/Projects/ft5955-independent-build-check"
# Original checkout has local changes; DO NOT switch, reset or stash it.
# origin/main was already fetched into the original checkout.
TEST="$HOME/Projects/ft5955-poll100-build"
git -C "$REPO" worktree add --detach "$TEST" origin/main &&
python3 "$TEST/tools/verify_ft5955_clean_clone.py" --stage --poll-100ms
```

This neither installs nor operates the fingerprint reader. Only after this build passes should the user elect to run `bash "$REPO/tools/ft5955_kde_trial.sh" --start-poll100`; the rollback is `bash "$REPO/tools/ft5955_kde_trial.sh" --stop`. Neither command changes PAM. The existing staged baseline binary and source checkout remain preserved.

## Completed alternatives to avoid revisiting

- An extra hardened `ft5955-engine-smoke.service` with a fake engine **passed** non-root socket/UID tests, but **nested bubblewrap inside that service failed** (`ERROR BWRAP_NAMESPACE_UNAVAILABLE`). Temporary units, socket and service account were removed. The team deliberately **stopped pursuing double sandboxing** and succeeded with the existing user-session MOH/bwrap route instead.
- USB Claim permissions in the earlier private test required a temporary ACL on the identified device node. The standard system service already had USB access; no separate physical unplug test is necessary.
- **GitHub housekeeping, 17 October:** [consolidation PR #4](https://github.com/Inforce855/focaltech-5955-linux/pull/4) was **merged into `main`** with full history; the fully represented earlier private-[`fprintd` PR #2](https://github.com/Inforce855/focaltech-5955-linux/pull/2) was **closed as superseded without deleting its branch**. The older [MOH engine research PR #1](https://github.com/Inforce855/focaltech-5955-linux/pull/1) stays **open** because it contains substantial additional `engine/` code and tests not yet reviewed for merging to `main`. **Do not delete those branches, run `git clean` in live trees, or rewrite the pinned snapshot.**

## Safe operational note

The **lab trial was fully rolled back**; no additional commands are needed to keep the normal system in its existing state. If a future trial is deliberately authorised, consult the actual [documented setup and stop scripts](kde-short-lived-trial-2026-10-17.md), check OS versions and exact rollback rather than assuming the environment has not changed. Never commit actual fingerprint data, vendor DLLs or sensitive logs.
